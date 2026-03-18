"""Jarvis AI cog: GPT-4o-mini with function calling, conversation memory, and tool dispatch."""
import asyncio
import json
import logging
from datetime import datetime, timezone

import discord
import openai
from discord.ext import commands
from openai import AsyncOpenAI

import config
from services import crypto as crypto_svc
from services import news as news_svc
from services import search as search_svc
from services import stocks as stocks_svc
from services import translate as translate_svc
from services import weather as weather_svc
from services import wikipedia as wikipedia_svc

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information. Use for recent events, facts, or when the user asks for up-to-date info.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}}, "required": ["query"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for a city or location. Supports current/forecast or historical when a date is given.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City or location name"},
                    "date": {
                        "type": "string",
                        "description": "Optional date in YYYY-MM-DD for historical weather (e.g. 2026-03-12). If omitted, returns current/forecast.",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock",
            "description": "Get stock quote (price, change, high/low) for a ticker symbol or company name, optionally with performance over a time range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol or company name (e.g. AAPL, MSFT).",
                    },
                    "range": {
                        "type": "string",
                        "description": "Optional performance range such as '1m', '3m', '6m', '1y', or 'ytd' when the user asks about performance over time (e.g. 'this year', 'last 3 months').",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto",
            "description": "Get cryptocurrency price and market data. Use symbol like 'btc', 'eth'. Empty string returns top coins. Can also include a range for performance over time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Crypto symbol (e.g. btc, eth) or empty for top list",
                    },
                    "range": {
                        "type": "string",
                        "description": "Optional performance range such as '1m', '3m', '6m', '1y', or 'ytd' when the user asks about performance over time (e.g. 'this year', 'last 3 months').",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wikipedia_lookup",
            "description": "Get a short Wikipedia summary for a topic.",
            "parameters": {"type": "object", "properties": {"topic": {"type": "string", "description": "Topic to look up"}}, "required": ["topic"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Get recent news headlines. Use when the user asks for news, headlines, or current events. Optional topic (e.g. 'technology', 'elections'); empty = top US headlines.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Topic or search term (e.g. 'technology'); empty string for top headlines"}}, "required": ["query"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_invite_link",
            "description": "Get the bot invite link when the user asks how to add Jarvis to another server.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "translate_text",
            "description": "Translate text into another language using DeepL. Use when the user asks to translate or to respond in a different language.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to translate."},
                    "target_lang": {
                        "type": "string",
                        "description": "Target language code (e.g. EN, DE, FR, ES, PT-BR, JA, ZH).",
                    },
                    "source_lang": {
                        "type": "string",
                        "description": "Optional source language code; if omitted DeepL will auto-detect.",
                    },
                    "formality": {
                        "type": "string",
                        "description": "Optional: 'default', 'more', or 'less' formality (where supported).",
                    },
                },
                "required": ["text", "target_lang"],
            },
        },
    },
]

# Cache the last API results by a Jarvis "session" key so we can
# render rich embeds after the language model responds.
LAST_NEWS_BY_SESSION: dict[str, dict] = {}
LAST_WEATHER_BY_SESSION: dict[str, dict] = {}
LAST_STOCK_BY_SESSION: dict[str, dict] = {}
LAST_CRYPTO_BY_SESSION: dict[str, dict] = {}

JARVIS_SYSTEM = (
    "You are Jarvis, a helpful, concise AI assistant running inside a Discord bot. "
    "You have access to tools: web_search, get_weather, get_stock, get_crypto, wikipedia_lookup, get_news, translate_text, get_invite_link. Use them when they would help answer the user; cite sources briefly when appropriate. "
    "When the user asks for news, headlines, or current events (e.g. 'news about the world', 'what's the news on tech'), you MUST call get_news with the topic or query—never answer from memory; the tool fetches current headlines and they are shown in a rich embed. "
    "When the user asks about how a stock or crypto has performed over a period (e.g. 'this year', 'last 3 months'), call get_stock or get_crypto with an appropriate 'range' argument such as 'ytd', '1m', '3m', '6m', or '1y'. "
    "When the user asks for several different things (e.g. weather and news, or stock and crypto), call all relevant tools in the same turn so you can combine the information and list all sources. "
    "Always keep responses reasonably short and to the point, unless the user explicitly asks for more detail. "
    "Avoid tasks that would consume a very large number of tokens. If a user asks for something that would use an unusually large amount of tokens, politely decline and ask them to narrow or summarize their request instead."
)


async def _run_tool(name: str, arguments: dict) -> tuple[str, str]:
    """Execute one tool by name with given arguments. Returns (result_text, source_label)."""
    try:
        if name == "web_search":
            out = await asyncio.to_thread(
                search_svc.web_search, arguments.get("query", "")
            )
            return out, "DuckDuckGo"
        if name == "get_weather":
            session_key = arguments.pop("_jarvis_session", None)
            data = await weather_svc.get_weather_data(
                arguments.get("city", ""), config.WEATHER_API_KEY, arguments.get("date")
            )
            if session_key and "error" not in data:
                LAST_WEATHER_BY_SESSION[session_key] = data
            return weather_svc.format_weather_as_text(data), "WeatherAPI"
        if name == "get_stock":
            session_key = arguments.pop("_jarvis_session", None)
            data = await stocks_svc.get_stock_data(
                arguments.get("symbol", ""), config.FINNHUB_API_KEY, arguments.get("range")
            )
            if session_key and "error" not in data:
                LAST_STOCK_BY_SESSION[session_key] = data
            return stocks_svc.format_stock_as_text(data), "Finnhub"
        if name == "get_crypto":
            session_key = arguments.pop("_jarvis_session", None)
            data = await crypto_svc.get_crypto_data(
                arguments.get("name"),
                arguments.get("range"),
                api_key=config.COINGECKO_API_KEY,
            )
            if session_key and "error" not in data:
                LAST_CRYPTO_BY_SESSION[session_key] = data
            return crypto_svc.format_crypto_as_text(data), "CoinGecko"
        if name == "wikipedia_lookup":
            data = await asyncio.to_thread(
                wikipedia_svc.wikipedia_lookup, arguments.get("topic", "")
            )
            return wikipedia_svc.format_wikipedia_as_text(data), "Wikipedia"
        if name == "get_news":
            session_key = arguments.pop("_jarvis_session", None)
            data = await news_svc.get_news_data(
                arguments.get("query"), config.NEWS_API_KEY
            )
            if session_key and "error" not in data:
                LAST_NEWS_BY_SESSION[session_key] = data
            # Omit direct URLs in the text so Discord doesn't auto-embed
            # each article; the rich paginated embeds handle links instead.
            return news_svc.format_news_as_text(data, include_urls=False), "NewsAPI"
        if name == "translate_text":
            data = await translate_svc.translate_text(
                text=arguments.get("text", ""),
                target_lang=arguments.get("target_lang", ""),
                api_key=config.DEEPL_API_KEY,
                source_lang=arguments.get("source_lang"),
                formality=arguments.get("formality"),
            )
            return translate_svc.format_translation_as_text(data), "DeepL"
        if name == "get_invite_link":
            return (
                f"Invite me to other servers using this link: {config.INVITE_LINK}",
                "Invite",
            )
    except Exception as e:
        logger.exception("Tool execution failed")
        return f"Tool error: {e}", name
    return "Unknown tool", ""


class Jarvis(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self._messages: dict[str, dict[str, list]] = {}

    async def _summarize_history(self, msgs: list) -> str:
        """Summarize conversation turns for context compression."""
        if len(msgs) <= 4:
            return ""
        to_summarize = msgs[1:-4]
        text_parts = []
        for m in to_summarize:
            role = m.get("role", "unknown")
            content = m.get("content") or ""
            if isinstance(content, str):
                text_parts.append(f"{role}: {content[:500]}")
        if not text_parts:
            return ""
        prompt = "Summarize this conversation in 3-5 bullet points, preserving key facts, names, and decisions.\n\n" + "\n\n".join(text_parts)
        try:
            r = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
            )
            return (r.choices[0].message.content or "").strip()
        except Exception:
            return ""

    async def _send_jarvis_response(
        self, ctx: commands.Context, response: str, used_sources: list[str]
    ) -> None:
        """Send response as plain message(s), splitting at 2000 chars if needed."""
        if not response.strip() and not used_sources:
            return
        body = (response.strip() or "")
        suffix = ("\nSources: " + ", ".join(used_sources)) if used_sources else ""
        body_parts = [body[i : i + 2000] for i in range(0, len(body), 2000)] if body else []
        if not body_parts:
            body_parts = [""]
        last = body_parts[-1] + suffix
        if len(last) > 2000:
            body_parts.append(suffix.strip())
        else:
            body_parts[-1] = last
        for part in body_parts:
            if part:
                await ctx.send(part)

    @commands.command(name="_jarvis_internal")
    async def jarvis(self, ctx: commands.Context, *, query: str = "") -> None:
        sender = str(ctx.message.author.id)
        if sender in config.BANNED_USER_IDS:
            await ctx.send(
                "I'm unable to respond—your account has reached its usage limit. "
                "Please try again later or contact support if you believe this is an error."
            )
            return
        raw_content = ctx.message.content
        if self.bot.user and self.bot.user in ctx.message.mentions:
            query = raw_content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()
        if not query:
            await ctx.send(
                "You can mention me as @Jarvis and ask things like:\n"
                "- what can you do?\n"
                "- what's the weather in New York (including past dates)?\n"
                "- how has AAPL or BTC performed this year (or over the last 3 months)?\n"
                "- show me today's news on technology or any topic.\n"
                "- search the web for an answer.\n"
                "- summarize or explain a Wikipedia topic.\n"
                "- translate this text to German (or any language).\n"
                "- flip a coin, roll a dice, or answer like a magic 8-ball.\n"
                "- chat about general questions, coding, or planning."
            )
            return
        server = str(ctx.message.guild)

        # Reply context: if user replied to a message, include it
        if ctx.message.reference and ctx.message.reference.message_id:
            try:
                ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                quoted = ref_msg.content or "(no text)"
                if ref_msg.attachments:
                    urls = [a.url for a in ref_msg.attachments]
                    quoted += "\nAttachments: " + ", ".join(urls)
                query = f"The user is replying to this message:\n\n> {quoted[:800]}\n\nUser question: {query}"
            except Exception:
                pass

        if len(query) > 1000 or len(query.split()) > 200:
            await ctx.send(
                "This request looks quite large and may exceed my usage limits. "
                "Please shorten or narrow down your question."
            )
            return

        now_utc = datetime.now(timezone.utc)
        today = now_utc.strftime("%A, %B %d, %Y")
        current_utc = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        system_message = {
            "role": "system",
            "content": (
                JARVIS_SYSTEM
                + f"\n\nToday's date is {today}. Current date and time in UTC: {current_utc}. "
                "When the user asks for the current time, date, or time in a city or timezone, use this UTC moment as the reference and compute the local time (e.g. Karachi = Pakistan Standard Time = UTC+5). Answer with the actual time; do not say you cannot provide it."
            ),
        }
        user_message = {"role": "user", "content": query}
        if server not in self._messages:
            self._messages[server] = {}
        if sender not in self._messages[server]:
            self._messages[server][sender] = [system_message, user_message]
        else:
            if len(self._messages[server][sender]) > 30:
                summary = await self._summarize_history(self._messages[server][sender])
                if summary:
                    last_four = self._messages[server][sender][-4:]
                    self._messages[server][sender] = [
                        system_message,
                        {"role": "user", "content": f"[Conversation summary]\n{summary}"},
                        {"role": "assistant", "content": "Understood. I'll continue from this summary."},
                        *last_four,
                    ]
            self._messages[server][sender].append(user_message)

        used_sources: list[str] = []
        max_retries = 3
        backoff = [2, 4, 8]
        msg_list = self._messages[server][sender]
        msg_list[0] = system_message

        async with ctx.typing():
            response_obj = None
            for attempt in range(max_retries + 1):
                try:
                    response_obj = await self._client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=msg_list,
                        tools=TOOLS,
                        tool_choice="auto",
                    )
                    break
                except Exception as api_err:
                    if isinstance(api_err, openai.RateLimitError) and attempt < max_retries:
                        await asyncio.sleep(backoff[attempt])
                        continue
                    if isinstance(api_err, openai.BadRequestError):
                        summary = await self._summarize_history(msg_list)
                        if summary:
                            msg_list = [system_message, {"role": "user", "content": f"[Summary]\n{summary}"}, *msg_list[-6:]]
                            self._messages[server][sender] = msg_list
                            await asyncio.sleep(1)
                            continue
                    await ctx.send(
                        embed=discord.Embed(
                            title="Error",
                            description="Something went wrong. Please try again later.",
                            color=0xE74C3C,
                        )
                    )
                    return
            if response_obj is None:
                await ctx.send(
                    embed=discord.Embed(
                        title="Error",
                        description="Something went wrong. Please try again later.",
                        color=0xE74C3C,
                    )
                )
                return

            choice = response_obj.choices[0]
            assistant_msg = choice.message
            tool_calls = getattr(assistant_msg, "tool_calls", None) or []

            while tool_calls:
                msg_list.append(assistant_msg)

                async def run_one(tc):
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except Exception:
                        args = {}
                    # Attach a Jarvis session key so tools can store
                    # structured results (e.g. news, weather, stocks, crypto) for this user.
                    if name in ("get_news", "get_weather", "get_stock", "get_crypto"):
                        args["_jarvis_session"] = f"{server}:{sender}"
                    result_text, source_label = await _run_tool(name, args)
                    return tc.id, result_text, source_label

                results = await asyncio.gather(*(run_one(tc) for tc in tool_calls))
                for tool_call_id, result_text, source_label in results:
                    if source_label and source_label not in used_sources:
                        used_sources.append(source_label)
                    msg_list.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_text,
                    })
                try:
                    response_obj = await self._client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=msg_list,
                        tools=TOOLS,
                        tool_choice="auto",
                    )
                except Exception:
                    await ctx.send(
                        embed=discord.Embed(
                            title="Error",
                            description="Tool lookup failed. Please try again.",
                            color=0xE74C3C,
                        )
                    )
                    return
                choice = response_obj.choices[0]
                assistant_msg = choice.message
                tool_calls = getattr(assistant_msg, "tool_calls", None) or []

            final_content = (assistant_msg.content or "").strip()
            if final_content:
                # Fallback: if the user clearly asked for news but the model didn't call get_news, fetch it so we can show the embed.
                session_key = f"{server}:{sender}"
                if "NewsAPI" not in used_sources and config.NEWS_API_KEY:
                    if any(kw in query_lower for kw in ("news", "headlines", "current events", "what's happening")):
                        topic = ""
                        if "news about" in query_lower:
                            topic = query.split("about", 1)[-1].split("?")[0].strip()
                        elif "news on" in query_lower:
                            topic = query.split("on", 1)[-1].split("?")[0].strip()
                        else:
                            words = [w for w in query.replace("?", "").split() if w.lower() not in ("whats", "what", "the", "news", "headlines", "me", "give", "show")]
                            topic = " ".join(words[:5]) if words else ""
                        data = await news_svc.get_news_data(topic or None, config.NEWS_API_KEY)
                        if "error" not in data:
                            LAST_NEWS_BY_SESSION[session_key] = data
                            used_sources.append("NewsAPI")
                # If the response used any rich-data API, only show the
                # embeds and suppress the text reply to avoid redundancy.
                if all(src not in used_sources for src in ("NewsAPI", "WeatherAPI", "Finnhub", "CoinGecko")):
                    await self._send_jarvis_response(ctx, final_content, used_sources)
                    self._messages[server][sender].append({"role": "assistant", "content": final_content})

                if "NewsAPI" in used_sources:
                    session_key = f"{server}:{sender}"
                    data = LAST_NEWS_BY_SESSION.get(session_key)
                    if data:
                        pages = news_svc.build_news_embeds(data)
                        if pages:
                            view = news_svc.NewsPaginatorView(pages)
                            await ctx.send(embed=pages[0], view=view)
                        LAST_NEWS_BY_SESSION.pop(session_key, None)

                if "WeatherAPI" in used_sources:
                    session_key = f"{server}:{sender}"
                    data = LAST_WEATHER_BY_SESSION.get(session_key)
                    if data:
                        embed = weather_svc.build_weather_embed(data)
                        await ctx.send(embed=embed)
                        LAST_WEATHER_BY_SESSION.pop(session_key, None)

                if "Finnhub" in used_sources:
                    session_key = f"{server}:{sender}"
                    data = LAST_STOCK_BY_SESSION.get(session_key)
                    if data:
                        embed = stocks_svc.build_stock_embed(data)
                        await ctx.send(embed=embed)
                        LAST_STOCK_BY_SESSION.pop(session_key, None)

                if "CoinGecko" in used_sources:
                    session_key = f"{server}:{sender}"
                    data = LAST_CRYPTO_BY_SESSION.get(session_key)
                    if data:
                        embed = crypto_svc.build_crypto_embed(data)
                        await ctx.send(embed=embed)
                        LAST_CRYPTO_BY_SESSION.pop(session_key, None)
            else:
                msg_list.append(assistant_msg)
                try:
                    response_obj = await self._client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=msg_list,
                    )
                except Exception:
                    await ctx.send(
                        embed=discord.Embed(
                            title="Error",
                            description="Something went wrong. Please try again later.",
                            color=0xE74C3C,
                        )
                    )
                    return
                accumulated = (response_obj.choices[0].message.content or "").strip()
                if accumulated:
                    msg_list.append({"role": "assistant", "content": accumulated})
                    self._messages[server][sender] = msg_list
                    await self._send_jarvis_response(ctx, accumulated, used_sources)
                else:
                    await ctx.send("I couldn't generate a response. Please try again.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Jarvis(bot))
