"""Discord bot entry point. Loads config, creates bot, loads cogs, runs."""
import asyncio
from datetime import datetime, time as dt_time, timezone
import logging
import time

import discord
from discord.ext import commands

import config
from services.top_movers_subscriptions import TopMoversSubscriptions
from services import stocks as stocks_svc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

intents = discord.Intents().all()
bot = commands.Bot(command_prefix="!", intents=intents)

top_movers_subs = TopMoversSubscriptions(config.JARVIS_MEMORY_DB_PATH)


async def load_extensions() -> None:
    await bot.load_extension("cogs.jarvis")


def _parse_utc_hh_mm(hh_mm: str) -> dt_time:
    """Parse `HH:MM` (UTC) into a datetime.time."""
    raw = (hh_mm or "").strip()
    if not raw:
        return dt_time(9, 0)
    try:
        hh_s, mm_s = raw.split(":", 1)
        hh = int(hh_s)
        mm = int(mm_s)
        hh = max(0, min(hh, 23))
        mm = max(0, min(mm, 59))
        return dt_time(hh, mm)
    except Exception:
        return dt_time(9, 0)


async def _run_top_movers_daily_scheduler() -> None:
    """Post Top Movers embeds once daily to all subscribed channels."""
    target_t = _parse_utc_hh_mm(getattr(config, "TOP_MOVERS_DAILY_TIME_UTC", "09:00"))

    await top_movers_subs.init()
    await bot.wait_until_ready()

    # Loop forever; DB prevents re-sending for the same UTC date.
    while not bot.is_closed():
        try:
            now = datetime.now(timezone.utc)
            if now.time() >= target_t:
                today = now.date().isoformat()
                due = await top_movers_subs.get_due_subscriptions(today_utc_date=today)
                if due:
                    # Fetch once per day, send embed to many channels.
                    if not (config.ALPHAVANTAGE_API_KEY and config.ALPHAVANTAGE_API_KEY.strip()):
                        logger.warning("TOP MOVERS skipped: missing ALPHAVANTAGE_API_KEY")
                        # Avoid hammering the API on repeated checks.
                        await asyncio.sleep(60)
                        continue

                    data = await stocks_svc.get_stock_movers(
                        api_key=config.ALPHAVANTAGE_API_KEY,
                        direction="both",
                        top_n=getattr(config, "TOP_MOVERS_TOP_N", 5),
                        region=getattr(config, "TOP_MOVERS_REGION", "US"),
                    )
                    embed = stocks_svc.build_stock_embed(data)

                    # Send independently per channel; only mark sent on success.
                    sent_any = False
                    for row in due:
                        server_id = row["server_id"]
                        channel_id = row["channel_id"]
                        try:
                            ch = bot.get_channel(int(channel_id))
                            if ch is None:
                                ch = await bot.fetch_channel(int(channel_id))
                            await ch.send(embed=embed)
                            sent_any = True
                            await top_movers_subs.mark_sent(
                                server_id=server_id,
                                channel_id=channel_id,
                                sent_date_utc=today,
                            )
                        except Exception:
                            logger.exception(
                                "Failed sending top movers embed",
                                extra={"server_id": server_id, "channel_id": channel_id},
                            )

                    if sent_any:
                        logger.info("Posted daily top movers", extra={"channels": len(due)})
                    elif due:
                        # If every send failed, back off to avoid rate-limiting the
                        # market data API while permissions/config are wrong.
                        await asyncio.sleep(300)
                        continue
        except Exception:
            logger.exception("Top movers scheduler loop failed")

        # Check again soon; DB makes the operation idempotent for a given day.
        await asyncio.sleep(60)


@bot.command(name="subscribe")
@commands.guild_only()
async def top_movers_subscribe(ctx: commands.Context, channel: discord.TextChannel) -> None:
    """Admin-only: subscribe a channel to daily Top Movers embeds."""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Only server admins can use this command.")
        return

    if ctx.guild is None:
        await ctx.send("This command can only be used in a server.")
        return

    if channel.guild.id != ctx.guild.id:
        await ctx.send("Pick a channel from this server.")
        return

    was_new = await top_movers_subs.add_subscription(
        server_id=str(ctx.guild.id),
        channel_id=str(channel.id),
        subscribed_by=str(ctx.author.id),
    )
    await ctx.send(f"{'Subscribed' if was_new else 'Updated'} {channel.mention} to daily Top Movers.")


@bot.command(name="unsubscribe")
@commands.guild_only()
async def top_movers_unsubscribe(ctx: commands.Context, channel: discord.TextChannel) -> None:
    """Admin-only: unsubscribe a channel from daily Top Movers embeds."""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Only server admins can use this command.")
        return

    if ctx.guild is None:
        await ctx.send("This command can only be used in a server.")
        return

    if channel.guild.id != ctx.guild.id:
        await ctx.send("Pick a channel from this server.")
        return

    removed = await top_movers_subs.remove_subscription(
        server_id=str(ctx.guild.id),
        channel_id=str(channel.id),
    )
    if removed:
        await ctx.send(f"Unsubscribed {channel.mention} from daily Top Movers.")
    else:
        await ctx.send(f"{channel.mention} was not subscribed.")


@bot.event
async def on_ready() -> None:
    await bot.change_presence(activity=discord.Game("@Jarvis"))

    # Start scheduler once.
    if not getattr(bot, "_top_movers_scheduler_task", None):
        bot._top_movers_scheduler_task = asyncio.create_task(_run_top_movers_daily_scheduler())


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author == bot.user:
        return

    # Mention-only command routing.
    if bot.user in message.mentions:
        ctx = await bot.get_context(message)
        jarvis_cmd = bot.get_command("_jarvis_internal")
        if jarvis_cmd:
            await ctx.invoke(jarvis_cmd)
        return

    # For normal `!` commands, let discord.py handle prefix parsing.
    await bot.process_commands(message)


async def main() -> None:
    await load_extensions()
    try:
        await bot.start(config.DISCORD_TOKEN)
    finally:
        from services import news as news_svc

        await news_svc.close_news_http_session()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception("Bot crashed")
        print("An error occurred. Restarting the bot in 5 seconds.")
        time.sleep(5)
        raise
