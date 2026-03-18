from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import os
import random
import time
from datetime import datetime
from urllib.parse import quote

import discord
import openai
import requests
import wikipedia
from discord.ext import commands
from openai import AsyncOpenAI

from crypto import crypto
from ddgs import DDGS
from helpfunc import hlp
from stocks import stocks
from weather import wthr

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")
BANNED_USER_IDS = set(x.strip() for x in os.getenv("BANNED_USER_IDS", "").split(",") if x.strip())
intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

gptClientAsync = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
messages = dict()

# --- Jarvis tool implementations (sync, return plain text for GPT) ---
def _tool_web_search(query: str) -> str:
    return _web_search_sync(query)

def _tool_weather(city: str) -> str:
    try:
        url = f"https://api.weatherapi.com/v1/forecast.json?key={os.getenv('WEATHER_API_KEY')}&q={city}&aqi=no"
        r = requests.get(url)
        data = r.json()
        if "error" in data:
            return f"Weather error: {data['error'].get('message', 'Unknown')}"
        cur = data["current"]
        loc = data["location"]
        cond = cur["condition"]
        day = data["forecast"]["forecastday"][0]["day"]
        return (
            f"{loc['name']}, {loc['region']}, {loc['country']}: {cur['temp_f']}°F (feels like {cur['feelslike_f']}°F), "
            f"{cond['text']}. High {day['maxtemp_f']}°F, Low {day['mintemp_f']}°F. "
            f"Humidity {cur['humidity']}%, wind {cur['wind_mph']} mph {cur['wind_dir']}. "
            f"Chance of rain {day['daily_chance_of_rain']}%."
        )
    except Exception as e:
        return f"Weather lookup failed: {e}"

def _tool_stock(symbol: str) -> str:
    try:
        base = "https://finnhub.io/api/v1/"
        token = f"&token={os.getenv('FINNHUB_API_KEY')}"
        search = requests.get(base + f"search?q={symbol}{token}").json()
        if not search.get("result"):
            return f"No stock found for symbol: {symbol}"
        s = search["result"][0]
        info = requests.get(base + f"quote?symbol={s['symbol']}{token}").json()
        return (
            f"{s['description']} ({s['symbol']}): ${info['c']} (change ${info['d']}, {info['dp']}%). "
            f"High ${info['h']}, Low ${info['l']}, Open ${info['o']}, Previous close ${info['pc']}."
        )
    except Exception as e:
        return f"Stock lookup failed: {e}"

def _tool_crypto(name: str) -> str:
    try:
        base = "https://data.messari.io/api/v1/assets"
        if not name or name.strip() == "":
            r = requests.get(base)
            data = r.json()
            lines = []
            for x in data.get("data", [])[:10]:
                lines.append(f"{x['name']} ({x['symbol']}): ${round(x['metrics']['market_data']['price_usd'], 5)}")
            return "\n".join(lines) if lines else "No crypto data."
        r = requests.get(base + f"/{name.strip().lower()}/metrics")
        data = r.json()
        d = data["data"]
        m = d["market_data"]
        price = m["price_usd"]
        return (
            f"{d['name']} ({d['symbol']}): ${round(price, 5)}. "
            f"24h: O ${round(m['ohlcv_last_24_hour']['open'], 5)} H ${round(m['ohlcv_last_24_hour']['high'], 5)} "
            f"L ${round(m['ohlcv_last_24_hour']['low'], 5)} C ${round(m['ohlcv_last_24_hour']['close'], 5)}."
        )
    except Exception as e:
        return f"Crypto lookup failed: {e}"

def _tool_wikipedia(topic: str) -> str:
    try:
        titles = wikipedia.search(topic.strip(), results=1)
        if not titles:
            return f"Wikipedia: no results for '{topic}'."
        page = wikipedia.page(title=titles[0], auto_suggest=False)
        return page.summary.split("\n")[0][:1500]
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Wikipedia: ambiguous. First option: {e.options[0]}"
    except wikipedia.exceptions.PageError:
        return f"Wikipedia: no page found for '{topic}'."
    except Exception as e:
        return f"Wikipedia lookup failed: {e}"

def _tool_news(query: str) -> str:
    """Fetch headline news from NewsAPI. Optional topic; empty = top US headlines."""
    try:
        key = os.getenv("NEWS_API_KEY", "").strip()
        if not key:
            return "News API is not configured (missing NEWS_API_KEY)."
        if query and query.strip():
            url = f"https://newsapi.org/v2/top-headlines?language=en&q={quote(query.strip())}&pageSize=5&apiKey={key}"
        else:
            url = f"https://newsapi.org/v2/top-headlines?country=us&pageSize=5&apiKey={key}"
        r = requests.get(url)
        data = r.json()
        if data.get("status") == "error":
            return f"News API error: {data.get('message', 'Unknown')}"
        articles = data.get("articles") or []
        if not articles:
            return "No news articles found for that topic."
        lines = []
        for i, a in enumerate(articles[:5], 1):
            src = (a.get("source") or {}).get("name", "Unknown")
            title = (a.get("title") or "").strip() or "(No title)"
            desc = (a.get("description") or "").strip() or ""
            url_link = (a.get("url") or "").strip()
            block = f"[{i}] {title} — {src}"
            if desc:
                block += f"\n{desc[:300]}{'...' if len(desc) > 300 else ''}"
            if url_link:
                block += f"\n{url_link}"
            lines.append(block)
        return "\n\n".join(lines)
    except Exception as e:
        return f"News lookup failed: {e}"

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
            "description": "Get current weather and forecast for a city or location.",
            "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": "City or location name"}}, "required": ["city"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock",
            "description": "Get stock quote (price, change, high/low) for a ticker symbol or company name.",
            "parameters": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Ticker symbol or company name"}}, "required": ["symbol"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto",
            "description": "Get cryptocurrency price and market data. Use symbol like 'btc', 'eth'. Empty string returns top coins.",
            "parameters": {"type": "object", "properties": {"name": {"type": "string", "description": "Crypto symbol (e.g. btc, eth) or empty for top list"}}, "required": ["name"]},
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
]

def _run_tool(name: str, arguments: dict) -> tuple[str, str]:
    """Execute one tool by name with given arguments. Returns (result_text, source_label)."""
    try:
        if name == "web_search":
            out = _tool_web_search(arguments.get("query", ""))
            return out, "DuckDuckGo"
        if name == "get_weather":
            out = _tool_weather(arguments.get("city", ""))
            return out, "WeatherAPI"
        if name == "get_stock":
            out = _tool_stock(arguments.get("symbol", ""))
            return out, "Finnhub"
        if name == "get_crypto":
            out = _tool_crypto(arguments.get("name", ""))
            return out, "Messari"
        if name == "wikipedia_lookup":
            out = _tool_wikipedia(arguments.get("topic", ""))
            return out, "Wikipedia"
        if name == "get_news":
            out = _tool_news(arguments.get("query", ""))
            return out, "NewsAPI"
    except Exception as e:
        return f"Tool error: {e}", name
    return "Unknown tool", ""

@bot.event
async def on_ready():
    game = discord.Game("!help")
    await bot.change_presence(activity=game)
    for guild in bot.guilds:
        if guild.name == GUILD:
            break

def _web_search_sync(query: str, max_results: int = 5, max_context_chars: int = 2000) -> str:
    """Run DuckDuckGo search and return formatted snippets (sync, for use in thread)."""
    try:
        results = DDGS().text(query, max_results=max_results)
        results = list(results) if results else []
        if not results:
            return ""
        lines = []
        total = 0
        for i, r in enumerate(results[:max_results], 1):
            title = r.get("title", "")
            body = (r.get("body") or "")[:400]
            href = r.get("href", "")
            block = f"[{i}] {title}\n{body}\nSource: {href}"
            if total + len(block) > max_context_chars:
                break
            lines.append(block)
            total += len(block)
        return "\n\n".join(lines) if lines else ""
    except Exception as e:
        print(f"[Jarvis] Web search error: {e}", flush=True)
        return f"[Web search failed: {e}]"

JARVIS_SYSTEM = (
    "You are Jarvis, a helpful, concise AI assistant running inside a Discord bot. "
    "You have access to tools: web_search, get_weather, get_stock, get_crypto, wikipedia_lookup, get_news. Use them when they would help answer the user; cite sources briefly when appropriate. "
    "When the user asks for several different things (e.g. weather and news, or stock and crypto), call all relevant tools in the same turn so you can combine the information and list all sources. "
    "Always keep responses reasonably short and to the point, unless the user explicitly asks for more detail. "
    "Avoid tasks that would consume a very large number of tokens. If a user asks for something that would use an unusually large amount of tokens, politely decline and ask them to narrow or summarize their request instead."
)

async def _summarize_history(msgs: list) -> str:
    """Summarize conversation turns (exclude system and last few) for context compression."""
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
        r = await gptClientAsync.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return ""

async def _send_jarvis_response(ctx, response: str, used_sources: list, query: str):
    """Send response as plain message(s), splitting at 2000 chars if needed. Sources appended to last message."""
    if not response.strip() and not used_sources:
        return
    body = (response.strip() or "")
    suffix = ("\nSources: " + ", ".join(used_sources)) if used_sources else ""
    body_parts = [body[i : i + 2000] for i in range(0, len(body), 2000)] if body else []
    if not body_parts:
        body_parts = [""]
    last = body_parts[-1] + suffix
    if len(last) > 2000:
        body_parts[-1] = body_parts[-1]
        body_parts.append(suffix.strip())
    else:
        body_parts[-1] = last
    for part in body_parts:
        if part:
            await ctx.send(part)

@bot.command(name='jarvis')
async def gpt(ctx):
    sender = str(ctx.message.author.id)
    if sender in BANNED_USER_IDS:
        await ctx.send("I'm unable to respond—your account has reached its usage limit. Please try again later or contact support if you believe this is an error.")
        return
    raw_content = ctx.message.content
    if "!jarvis " in raw_content:
        query = raw_content.split("!jarvis ", 1)[1].strip()
    elif bot.user in ctx.message.mentions:
        # @Jarvis trigger: strip bot mention to get the question
        query = raw_content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
    else:
        await ctx.send("Please ask your question after `!jarvis` or by mentioning me (@Jarvis).")
        return
    if not query:
        await ctx.send("Please provide a question after `!jarvis` or my mention.")
        return
    server = str(ctx.message.guild)

    # Reply context (E): if user replied to a message, include it
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
        await ctx.send("This request looks quite large and may exceed my usage limits. Please shorten or narrow down your question.")
        return

    today = datetime.now().strftime("%A, %B %d, %Y")
    system_message = {
        "role": "system",
        "content": JARVIS_SYSTEM + f"\n\nToday's date is {today}. When the user asks for the current year, date, or time, use this date.",
    }
    user_message = {"role": "user", "content": query}
    if server not in messages:
        messages[server] = dict()
    if sender not in messages[server]:
        messages[server][sender] = [system_message, user_message]
    else:
        # Smarter memory (C): summarize when > 30 messages instead of chopping
        if len(messages[server][sender]) > 30:
            summary = await _summarize_history(messages[server][sender])
            if summary:
                last_four = messages[server][sender][-4:]
                messages[server][sender] = [
                    system_message,
                    {"role": "user", "content": f"[Conversation summary]\n{summary}"},
                    {"role": "assistant", "content": "Understood. I'll continue from this summary."},
                    *last_four,
                ]
        messages[server][sender].append(user_message)

    used_sources = []
    max_retries = 3
    backoff = [2, 4, 8]

    async with ctx.typing():
        msg_list = messages[server][sender]
        msg_list[0] = system_message  # refresh so every request has current date
        response_obj = None
        for attempt in range(max_retries + 1):
            try:
                response_obj = await gptClientAsync.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=msg_list,
                    tools=TOOLS,
                    tool_choice="auto",
                )
                break
            except Exception as api_err:
                try:
                    if isinstance(api_err, openai.RateLimitError) and attempt < max_retries:
                        await asyncio.sleep(backoff[attempt])
                        continue
                    if isinstance(api_err, openai.BadRequestError):
                        summary = await _summarize_history(msg_list)
                        if summary:
                            msg_list = [system_message, {"role": "user", "content": f"[Summary]\n{summary}"}, *msg_list[-6:]]
                            messages[server][sender] = msg_list
                            await asyncio.sleep(1)
                            continue
                except Exception:
                    pass
                await ctx.send(embed=discord.Embed(title="Error", description="Something went wrong. Please try again later.", color=0xE74C3C))
                return
        if response_obj is None:
            await ctx.send(embed=discord.Embed(title="Error", description="Something went wrong. Please try again later.", color=0xE74C3C))
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
                result_text, source_label = await asyncio.to_thread(_run_tool, name, args)
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
                response_obj = await gptClientAsync.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=msg_list,
                    tools=TOOLS,
                    tool_choice="auto",
                )
            except Exception as e:
                await ctx.send(embed=discord.Embed(title="Error", description="Tool lookup failed. Please try again.", color=0xE74C3C))
                return
            choice = response_obj.choices[0]
            assistant_msg = choice.message
            tool_calls = getattr(assistant_msg, "tool_calls", None) or []

        final_content = (assistant_msg.content or "").strip()
        if len(final_content) > 0:
            await _send_jarvis_response(ctx, final_content, used_sources, query[:256])
            messages[server][sender].append({"role": "assistant", "content": final_content})
        else:
            msg_list.append(assistant_msg)
            try:
                response_obj = await gptClientAsync.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=msg_list,
                )
            except Exception:
                await ctx.send(embed=discord.Embed(title="Error", description="Something went wrong. Please try again.", color=0xE74C3C))
                return
            accumulated = (response_obj.choices[0].message.content or "").strip()
            if accumulated:
                msg_list.append({"role": "assistant", "content": accumulated})
                messages[server][sender] = msg_list
                await _send_jarvis_response(ctx, accumulated, used_sources, query[:256])
            else:
                await ctx.send("I couldn't generate a response. Please try again.")

########

@bot.command(name='help')
async def help(ctx):
    await ctx.send(hlp())

########

@bot.command(name='weather')
async def wethr(ctx):
    await wthr(ctx)

########

@bot.command(name='invite')
async def invite(ctx):
    await ctx.send('Invite me to other servers using this link: https://discord.com/api/oauth2/authorize?client_id=800094180041818112&permissions=8&scope=bot')

########
            
greet = ['Hi ', 'Hello ', 'What\'s up, ', 'Greetings, ', 'Sup ', 'Howdy ', 'Hey ']

ball = ['As I see it, yes.', 'Ask again later.','Better not tell you now.','Cannot predict now.','Concentrate and ask again.','Don’t count on it.','It is certain.','It is decidedly so.','Most likely.','My reply is no.','My sources say no.','Outlook not so good.','Outlook good.','Reply hazy, try again.','Signs point to yes.','Very doubtful.','Without a doubt.','Yes.','Yes – definitely.','You may rely on it.']

########

@bot.command(name='dice')
async def dice(ctx):
    await ctx.send(random.randint(1, 6))

########
    
@bot.command(name='coin')
async def coin(ctx):
    await ctx.send(random.choice(['Heads!', 'Tails!']))

########

@bot.command(name='8ball')
async def eightball(ctx):
    await ctx.send(random.choice(ball))

########

@bot.command(name='crypto')
async def cryp(ctx):
    await crypto(ctx)

########

@bot.command(name='stocks')
async def stocks_cmd(ctx):
    await stocks(ctx)

########

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

########
    
    if message.content.startswith('hey jarvis') or message.content.startswith('hi jarvis') or message.content.startswith('hello jarvis') or message.content.startswith('sup jarvis') or message.content.startswith('yo jarvis'):
        mention = message.author.mention
        await message.channel.send(random.choice(greet)+mention)

########

    if message.content.startswith('thanks jarvis') or message.content.startswith('thank you jarvis'):
        await message.channel.send('You\'re welcome')
        
########

    if message.content.startswith('jarvis i love you'):
        await message.channel.send('I love you, too')

########

    if message.content.startswith('how are you jarvis') or message.content.startswith('how are you doing jarvis'):
        await message.channel.send('I\'m doing quite well.')
        
########

    if message.content.startswith('jarvis shut up') or message.content.startswith('shut up jarvis'):
        await message.channel.send(':(')

########

    if message.content.startswith('jarvis tell me a joke'):
        a = requests.get("https://joke.deno.dev/").json()
        await message.channel.send(a["setup"]+'\n'+'||'+a["punchline"]+'||')

########
    # @Jarvis mention: run Jarvis if the bot was mentioned and message isn't a command
    if bot.user in message.mentions and not message.content.strip().startswith("!"):
        ctx = await bot.get_context(message)
        await gpt(ctx)
        return

    await bot.process_commands(message)

try:
    bot.run(TOKEN)
except Exception as e:
    print("An error occured. Restarting the bot in 5 seconds.")
    time.sleep(5)
    print(e)
    exit()