import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any

import discord
from discord.ext import commands
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"^https?://", flags=re.IGNORECASE)

# Keep track of the latest music controls per guild so plain text commands
# can update the same embed (in addition to the button interactions).
LAST_MUSIC_VIEWS: dict[int, "MusicControlView"] = {}


@dataclass
class QueueItem:
    title: str
    audio_url: str
    thumbnail_url: str | None = None


# Simple per-guild FIFO queue.
MUSIC_QUEUES: dict[int, list[QueueItem]] = {}
MUSIC_QUEUE_LOCKS: dict[int, asyncio.Lock] = {}


def _get_queue_lock(guild_id: int) -> asyncio.Lock:
    return MUSIC_QUEUE_LOCKS.setdefault(guild_id, asyncio.Lock())


def _pick_best_audio_url(info: dict[str, Any]) -> str:
    """Pick the best audio-only stream URL from a yt-dlp info dict."""

    # When yt-dlp selects a format, the direct stream URL is often available as `url`.
    audio_url = info.get("url")
    if audio_url:
        return str(audio_url)

    formats = info.get("formats") or []
    audio_formats = []
    for f in formats:
        if not f:
            continue
        if not f.get("url"):
            continue
        # yt-dlp uses 'none' for video codec when it is audio-only.
        if f.get("vcodec") == "none":
            audio_formats.append(f)

    if not audio_formats:
        raise ValueError("No audio-only formats found")

    # Prefer higher bitrate/abr when available.
    audio_formats.sort(key=lambda f: float(f.get("abr") or f.get("tbr") or 0), reverse=True)
    best = audio_formats[0]
    url = best.get("url")
    if not url:
        raise ValueError("Best audio format had no URL")
    return str(url)


def _extract_youtube_audio(search_or_url: str) -> tuple[str, str, str | None]:
    """Resolve a YouTube query (or URL) into (title, direct audio URL, thumbnail_url)."""
    search_or_url = (search_or_url or "").strip()
    if not search_or_url:
        raise ValueError("Empty song query")

    # Notes:
    # - We intentionally request audio-only formats (bestaudio/best).
    # - We resolve the best stream URL and let discord.py/FFmpeg handle decoding.
    ydl_opts: dict[str, Any] = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
    }

    with YoutubeDL(ydl_opts) as ydl:
        if _URL_RE.match(search_or_url):
            info = ydl.extract_info(search_or_url, download=False)
        else:
            # First resolve the best matching video URL, then extract formats from that video.
            search_info = ydl.extract_info(f"ytsearch1:{search_or_url}", download=False)
            entries = (search_info or {}).get("entries") or []
            if not entries:
                raise ValueError("No YouTube results found")
            entry0 = entries[0] or {}
            target_url = entry0.get("webpage_url") or entry0.get("url") or entry0.get("id")
            if not target_url:
                raise ValueError("Could not resolve search result to a video URL")
            info = ydl.extract_info(target_url, download=False)

    if not info:
        raise ValueError("yt-dlp returned no info")

    title = info.get("title") or search_or_url
    audio_url = _pick_best_audio_url(info)
    thumbnail_url = info.get("thumbnail")
    if not thumbnail_url:
        thumbs = info.get("thumbnails") or []
        if thumbs and isinstance(thumbs, list):
            first = thumbs[0] or {}
            thumbnail_url = first.get("url")
    return str(title), audio_url, (str(thumbnail_url) if thumbnail_url else None)


async def _ensure_voice(ctx: commands.Context, voice_channel: discord.VoiceChannel) -> discord.VoiceClient:
    """Ensure the bot is connected to `voice_channel`."""
    assert ctx.guild
    voice_client: discord.VoiceClient | None = ctx.guild.voice_client
    if voice_client and voice_client.is_connected():
        if getattr(voice_client.channel, "id", None) != voice_channel.id:
            await voice_client.move_to(voice_channel)
        return voice_client
    return await voice_channel.connect()


async def _play_youtube_audio(
    *,
    client: discord.Client,
    guild: discord.Guild,
    voice_channel: discord.VoiceChannel,
    song_query: str,
    after_cb=None,
) -> str:
    """Join `voice_channel`, resolve `song_query` on YouTube, and start playback."""
    voice_client = guild.voice_client
    try:
        if voice_client and voice_client.is_connected():
            if getattr(voice_client.channel, "id", None) != voice_channel.id:
                await voice_client.move_to(voice_channel)
        else:
            voice_client = await voice_channel.connect()
    except Exception:
        raise RuntimeError("voice_connect_failed")

    # Resolve audio URL (yt-dlp) off the event loop.
    title, audio_url, _thumbnail_url = await asyncio.to_thread(_extract_youtube_audio, song_query)

    # Stop current playback if any.
    try:
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()
    except Exception:
        logger.exception("Failed to stop existing playback")

    ffmpeg_before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    source = discord.FFmpegPCMAudio(audio_url, before_options=ffmpeg_before_options)

    try:
        voice_client.play(source, after=after_cb)
    except Exception as e:
        raise RuntimeError(f"ffmpeg_play_failed:{e}")

    return title


async def _start_playback_item(
    *,
    bot: commands.Bot,
    guild_id: int,
    guild: discord.Guild,
    voice_client: discord.VoiceClient,
    queue_item: QueueItem,
) -> None:
    """Start playing an already-resolved queue item."""
    view = LAST_MUSIC_VIEWS.get(guild_id)
    if view:
        view.title = queue_item.title
        view.thumbnail_url = queue_item.thumbnail_url
        view.status = "Playing"
        view._apply_button_states()

        if view.message:
            try:
                await view.message.edit(embed=view._make_embed(), view=view)
            except Exception:
                pass

    ffmpeg_before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    source = discord.FFmpegPCMAudio(queue_item.audio_url, before_options=ffmpeg_before_options)

    def _after_track_end(err: Exception | None) -> None:
        # after-callback is executed in a different thread.
        try:
            bot.loop.call_soon_threadsafe(
                lambda: bot.loop.create_task(_handle_track_end(bot, guild_id, err))
            )
        except Exception:
            pass

    voice_client.play(source, after=_after_track_end)


async def _start_next_from_queue(
    *,
    bot: commands.Bot,
    guild: discord.Guild,
    voice_channel: discord.VoiceChannel,
) -> bool:
    """Pop the next track from the guild queue and start it."""
    # Ensure we are connected to the right channel before starting.
    voice_client: discord.VoiceClient | None = guild.voice_client
    if voice_client and voice_client.is_connected():
        if getattr(voice_client.channel, "id", None) != voice_channel.id:
            await voice_client.move_to(voice_channel)
    else:
        voice_client = await voice_channel.connect()

    lock = _get_queue_lock(guild.id)
    async with lock:
        q = MUSIC_QUEUES.get(guild.id) or []
        if not q:
            return False
        next_item = q.pop(0)
        MUSIC_QUEUES[guild.id] = q

    await _start_playback_item(
        bot=bot,
        guild_id=guild.id,
        guild=guild,
        voice_client=voice_client,
        queue_item=next_item,
    )
    return True


async def _handle_track_end(
    bot: commands.Bot,
    guild_id: int,
    err: Exception | None,
) -> None:
    """Advance the queue when a track finishes."""
    if err:
        logger.error("Playback finished with error: %s", err)

    guild = bot.get_guild(guild_id)
    if not guild:
        return

    voice_client: discord.VoiceClient | None = guild.voice_client
    if not voice_client or not voice_client.is_connected():
        # If we got disconnected, don't try to continue the queue.
        async with _get_queue_lock(guild_id):
            MUSIC_QUEUES.pop(guild_id, None)
        return

    # Decide next track under lock.
    next_item: QueueItem | None = None
    async with _get_queue_lock(guild_id):
        q = MUSIC_QUEUES.get(guild_id) or []
        if q:
            next_item = q.pop(0)
            MUSIC_QUEUES[guild_id] = q

    if next_item is None:
        # Queue is empty: mark finished unless the user stopped/left.
        view = LAST_MUSIC_VIEWS.get(guild_id)
        if view and view.status not in ("Stopped", "Left", "Controls expired"):
            view.status = "Finished"
            view._apply_button_states()
            if view.message:
                try:
                    await view.message.edit(embed=view._make_embed(), view=view)
                except Exception:
                    pass
        return

    # Start next track from the queue.
    # Use the bot's current channel for continuity.
    voice_channel = voice_client.channel
    if not voice_channel:
        return
    await _start_playback_item(
        bot=bot,
        guild_id=guild_id,
        guild=guild,
        voice_client=voice_client,
        queue_item=next_item,
    )


class MusicControlView(discord.ui.View):
    def __init__(
        self,
        *,
        bot: commands.Bot,
        guild_id: int,
        requester_id: int,
        channel: discord.abc.Messageable,
        song_query: str,
        title: str,
        thumbnail_url: str | None,
        timeout: float = 600,
    ):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.requester_id = requester_id
        self.channel = channel
        self.song_query = song_query
        self.title = title
        self.thumbnail_url = thumbnail_url
        self.message: discord.Message | None = None
        self.status: str = "Playing"

    def _make_embed(self) -> discord.Embed:
        embed = discord.Embed(title="Music", description=f"Now playing: {self.title}", color=0x1ABC9C)
        if self.thumbnail_url:
            embed.set_thumbnail(url=self.thumbnail_url)
        embed.add_field(name="Status", value=self.status, inline=False)
        embed.set_footer(text="Controls are enabled for anyone in the same voice channel as the bot.")
        return embed

    async def _guard(self, interaction: discord.Interaction) -> bool:
        if not interaction.user:
            await interaction.response.send_message("Unknown user.", ephemeral=True)
            return False

        # Anyone in the same voice channel as the bot can control playback.
        guild = interaction.guild
        if not guild or not guild.voice_client or not guild.voice_client.is_connected():
            await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)
            return False
        user_voice = getattr(interaction.user, "voice", None)
        if not user_voice or not user_voice.channel:
            await interaction.response.send_message("Join my voice channel to control playback.", ephemeral=True)
            return False

        bot_channel = guild.voice_client.channel
        if not bot_channel:
            await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)
            return False

        if user_voice.channel.id != bot_channel.id:
            await interaction.response.send_message("You're not in my voice channel.", ephemeral=True)
            return False

        return True

    async def on_timeout(self) -> None:
        # Disable controls when the view expires.
        self.status = "Controls expired"
        self._disable_all_items()
        if self.message:
            try:
                await self.message.edit(embed=self._make_embed(), view=self)
            except Exception:
                pass

    def _disable_all_items(self) -> None:
        for item in self.children:
            try:
                item.disabled = True
            except Exception:
                continue

    def _apply_button_states(self) -> None:
        """
        Update which buttons are enabled based on `self.status`.

        We intentionally keep `Leave` enabled after stopping so the user can
        disconnect even when playback is paused/stopped.
        """
        # Default: enable everything.
        for item in self.children:
            try:
                item.disabled = False
            except Exception:
                continue

        if self.status in ("Left", "Controls expired"):
            self._disable_all_items()
            return

        if self.status in ("Stopped", "Finished"):
            # Disable Stop + Skip, keep Play/Pause + Leave enabled.
            for item in self.children:
                label = getattr(item, "label", None)
                if label in ("Stop", "Skip"):
                    try:
                        item.disabled = True
                    except Exception:
                        pass
            return

        # For "Playing" and "Paused", keep Play/Pause + Stop + Leave enabled.

    async def _update_message(self, interaction: discord.Interaction) -> None:
        if self.message:
            self._apply_button_states()
            await self.message.edit(embed=self._make_embed(), view=self)

    def _after_play_update(self, err: Exception | None) -> None:
        # Runs in a separate thread; schedule a UI update on the bot loop.
        if err:
            logger.error("Playback finished with error: %s", err)
        if not self.message:
            return

        async def _mark_done() -> None:
            # Avoid overriding explicit states triggered by stop/leave.
            if self.status not in ("Stopped", "Left", "Controls expired"):
                self.status = "Finished"
                self._apply_button_states()
            try:
                await self.message.edit(embed=self._make_embed(), view=self)
            except Exception:
                pass

        try:
            self.bot.loop.call_soon_threadsafe(lambda: self.bot.loop.create_task(_mark_done()))
        except Exception:
            pass

    @discord.ui.button(label="Play/Pause", style=discord.ButtonStyle.primary)
    async def play_pause_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._guard(interaction):
            return
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("No guild context.", ephemeral=True)
            return
        vc: discord.VoiceClient | None = guild.voice_client
        # Toggle behavior:
        # - if playing: pause
        # - if paused: resume
        # - otherwise: start playback (from current song_query)
        if vc and vc.is_connected() and vc.is_playing():
            vc.pause()
            self.status = "Paused"
            await interaction.response.defer()
            await self._update_message(interaction)
            return

        if vc and vc.is_connected() and vc.is_paused():
            vc.resume()
            self.status = "Playing"
            await interaction.response.defer()
            await self._update_message(interaction)
            return

        # If we're not currently playing/paused, start the next track from the queue.
        voice_channel: discord.VoiceChannel | None = None
        if vc and vc.is_connected():
            voice_channel = vc.channel
        if not voice_channel:
            if not interaction.user or not getattr(interaction.user, "voice", None) or not interaction.user.voice:
                await interaction.response.send_message("Join a voice channel to start playback.", ephemeral=True)
                return
            if not interaction.user.voice.channel:
                await interaction.response.send_message("Join a voice channel to start playback.", ephemeral=True)
                return
            voice_channel = interaction.user.voice.channel

        await interaction.response.defer()
        started = await _start_next_from_queue(
            bot=self.bot,
            guild=guild,
            voice_channel=voice_channel,
        )
        if not started:
            await interaction.followup.send("Queue is empty. Use `play <song>` first.", ephemeral=True)
            return
        # _start_playback_item updates the embed itself, but keep state consistent.
        await self._update_message(interaction)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary)
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._guard(interaction):
            return
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("No guild context.", ephemeral=True)
            return
        vc: discord.VoiceClient | None = guild.voice_client
        if not vc or not vc.is_connected():
            await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)
            return
        if vc.is_playing() or vc.is_paused():
            # Do NOT clear the queue; the track-end handler will start the next one.
            self.status = "Playing"
            await interaction.response.defer()
            vc.stop()
            await self._update_message(interaction)
            return
        await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._guard(interaction):
            return
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("No guild context.", ephemeral=True)
            return
        vc: discord.VoiceClient | None = guild.voice_client
        if not vc or not vc.is_connected():
            await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)
            return

        # Stop clears the queue.
        async with _get_queue_lock(guild.id):
            MUSIC_QUEUES.pop(guild.id, None)

        self.status = "Stopped"
        await interaction.response.defer()
        if vc.is_playing() or vc.is_paused():
            vc.stop()
        await self._update_message(interaction)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.primary)
    async def leave_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._guard(interaction):
            return
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("No guild context.", ephemeral=True)
            return
        vc: discord.VoiceClient | None = guild.voice_client
        if not vc or not vc.is_connected():
            await interaction.response.send_message("I'm not connected.", ephemeral=True)
            return

        async with _get_queue_lock(guild.id):
            MUSIC_QUEUES.pop(guild.id, None)

        await interaction.response.defer()
        try:
            try:
                await vc.disconnect(force=True)
            except TypeError:
                await vc.disconnect()
        except Exception:
            await interaction.followup.send("Couldn't disconnect cleanly.", ephemeral=True)
            return

        self.status = "Left"
        # Remove the view from the "latest view" cache since we're leaving.
        LAST_MUSIC_VIEWS.pop(guild.id, None)
        await self._update_message(interaction)


async def play_youtube_song(ctx: commands.Context, song_query: str) -> str:
    """Join ctx.author's voice channel and play a YouTube song with controls."""
    if not ctx.guild:
        await ctx.send("This command must be used inside a server.")
        return "Not in a server."
    if not ctx.author or not getattr(ctx.author, "voice", None) or not ctx.author.voice:
        await ctx.send("Join a voice channel first, then try `play <song>`.")  # pragma: no cover
        return "User not in a voice channel."
    if not ctx.author.voice.channel:
        await ctx.send("Join a voice channel first, then try `play <song>`.")  # pragma: no cover
        return "User not in a voice channel."

    voice_channel = ctx.author.voice.channel
    guild = ctx.guild

    # Resolve audio URL/title + thumbnail (yt-dlp) off the event loop.
    try:
        async with ctx.typing():
            title, audio_url, thumbnail_url = await asyncio.to_thread(_extract_youtube_audio, song_query)
    except Exception:
        await ctx.send("I couldn't find that on YouTube (or couldn't extract audio).")
        logger.exception("Failed to resolve YouTube audio")
        return "Couldn't resolve song on YouTube."

    queue_item = QueueItem(title=title, audio_url=audio_url, thumbnail_url=thumbnail_url)

    # Connect to voice + (optionally) move bot to the user's channel.
    try:
        await _ensure_voice(ctx, voice_channel)
    except Exception:
        await ctx.send("I couldn't connect to your voice channel. Do I have permission?")
        logger.exception("Failed to connect/move voice client")
        return

    vc: discord.VoiceClient = guild.voice_client  # type: ignore[assignment]

    # Enqueue and start immediately only if nothing is currently playing.
    lock = _get_queue_lock(guild.id)
    should_start_now = False
    start_item: QueueItem | None = None
    queued_position: int | None = None

    async with lock:
        q = MUSIC_QUEUES.setdefault(guild.id, [])
        q.append(queue_item)
        queued_position = len(q)

        if not (vc.is_playing() or vc.is_paused()):
            should_start_now = True
            start_item = q.pop(0)
            MUSIC_QUEUES[guild.id] = q

    if not should_start_now or start_item is None:
        # Already playing/paused: just queue it.
        await ctx.send(f"Queued #{queued_position}: {title}")
        return f"Queued #{queued_position}: {title}"

    # If we are starting a new track, ensure we have an active controls embed.
    view = LAST_MUSIC_VIEWS.get(guild.id)
    if not view:
        view = MusicControlView(
            bot=ctx.bot,
            guild_id=guild.id,
            requester_id=ctx.author.id,
            channel=ctx.channel,
            song_query=song_query,
            title=start_item.title,
                thumbnail_url=start_item.thumbnail_url,
        )
        embed = view._make_embed()
        try:
            msg = await ctx.send(embed=embed, view=view)
            view.message = msg
        except Exception:
            view.message = None
        LAST_MUSIC_VIEWS[guild.id] = view
    else:
        # Re-point the view to the latest channel for embed updates.
        view.channel = ctx.channel
        view.thumbnail_url = start_item.thumbnail_url

    try:
        await _start_playback_item(
            bot=ctx.bot,
            guild_id=guild.id,
            guild=guild,
            voice_client=vc,
            queue_item=start_item,
        )
    except Exception:
        await ctx.send("Playback failed. Is FFmpeg installed on the server?")
        logger.exception("FFmpeg/playback failed")
        return "Playback failed."

    return f"Now playing: {start_item.title}"


async def pause_voice(ctx: commands.Context) -> bool:
    """Pause current voice playback, if connected."""
    if not ctx.guild:
        return False
    voice_client: discord.VoiceClient | None = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await ctx.send("I'm not connected to a voice channel.")
        return True
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send("Paused.")
        # Best-effort: keep the interactive embed in sync.
        if ctx.guild and (view := LAST_MUSIC_VIEWS.get(ctx.guild.id)):
            view.status = "Paused"
            view._apply_button_states()
            try:
                if view.message:
                    await view.message.edit(embed=view._make_embed(), view=view)
            except Exception:
                pass
        return True
    if voice_client.is_paused():
        await ctx.send("Already paused.")
        return True
    await ctx.send("Nothing is playing right now.")
    return True


async def stop_voice(ctx: commands.Context) -> bool:
    """Stop current voice playback, if connected."""
    if not ctx.guild:
        return False
    voice_client: discord.VoiceClient | None = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await ctx.send("I'm not connected to a voice channel.")
        return True
    # Stopping clears the queue.
    if ctx.guild:
        async with _get_queue_lock(ctx.guild.id):
            MUSIC_QUEUES.pop(ctx.guild.id, None)

    view = ctx.guild and LAST_MUSIC_VIEWS.get(ctx.guild.id)
    if view:
        # Set status before calling `stop()` to avoid the track-end callback
        # briefly overwriting the UI as "Finished".
        view.status = "Stopped"
        view._apply_button_states()

    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()
    await ctx.send("Stopped.")
    if view:
        try:
            if view.message:
                await view.message.edit(embed=view._make_embed(), view=view)
        except Exception:
            pass
    return True


async def leave_voice(ctx: commands.Context) -> bool:
    """Disconnect the bot from the voice channel, if connected."""
    if not ctx.guild:
        return False
    voice_client: discord.VoiceClient | None = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await ctx.send("I'm not connected to a voice channel.")
        return True
    # Leaving clears the queue.
    if ctx.guild:
        async with _get_queue_lock(ctx.guild.id):
            MUSIC_QUEUES.pop(ctx.guild.id, None)

    try:
        await voice_client.disconnect(force=True)
    except TypeError:
        # discord.py versions may not support `force=`.
        await voice_client.disconnect()
    await ctx.send("Left the voice channel.")
    if ctx.guild and (view := LAST_MUSIC_VIEWS.pop(ctx.guild.id, None)):
        view.status = "Left"
        view._apply_button_states()
        try:
            if view.message:
                await view.message.edit(embed=view._make_embed(), view=view)
        except Exception:
            pass
    return True


async def skip_voice(ctx: commands.Context) -> bool:
    """Skip to the next track in the queue without clearing it."""
    if not ctx.guild:
        return False
    voice_client: discord.VoiceClient | None = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await ctx.send("I'm not connected to a voice channel.")
        return True
    if voice_client.is_playing() or voice_client.is_paused():
        view = LAST_MUSIC_VIEWS.get(ctx.guild.id)
        if view:
            view.status = "Playing"
            view._apply_button_states()
            try:
                if view.message:
                    await view.message.edit(embed=view._make_embed(), view=view)
            except Exception:
                pass
        voice_client.stop()
        await ctx.send("Skipped.")
        return True
    await ctx.send("Nothing is playing right now.")
    return True

