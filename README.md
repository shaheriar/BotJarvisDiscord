# Jarvis Discord Assistant

A Discord bot inspired by Iron Man's AI Jarvis. It can answer questions with GPT, search the web, fetch weather and stocks, look up Wikipedia, and more.

Add it to your server using this [invite link](https://discord.com/oauth2/authorize?client_id=800094180041818112&permissions=8&scope=bot).

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/shaheriar/BotJarvisDiscord
cd BotJarvisDiscord
pip install -r requirements.txt
```

### 2. Environment variables

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env` with your values:

| Variable | Description | Where to get it |
|----------|-------------|-----------------|
| `DISCORD_TOKEN` | Bot token | [Discord Developer Portal](https://discord.com/developers/applications) → your app → Bot → Token |
| `DISCORD_GUILD` | Your server ID | Discord: enable Developer Mode (Settings → Advanced), right‑click server name → Copy Server ID |
| `WEATHER_API_KEY` | Weather API | [weatherapi.com](https://www.weatherapi.com) — sign up, copy key from dashboard |
| `FINNHUB_API_KEY` | Stock data | [finnhub.io](https://finnhub.io) — register, copy key from dashboard |
| `NEWS_API_KEY` | News headlines (Jarvis tool) | [newsapi.org](https://newsapi.org) — register, copy key from dashboard |
| `OPENAI_API_KEY` | GPT for Jarvis | [platform.openai.com](https://platform.openai.com/api-keys) — create API key |
| `BANNED_USER_IDS` | Optional | Comma-separated Discord user IDs to block from Jarvis (e.g. `123,456`) |

### 3. Run the bot

```bash
python bot.py
```

---

## Commands

| Command | Description |
|---------|-------------|
| `!jarvis <question>` | Ask Jarvis anything. Uses GPT with web search, weather, stocks, crypto, news, and Wikipedia (define, summarize, search). |
| `@Jarvis <question>` | Same as above by mentioning the bot. |
| `!help` | List all commands. |
| `!weather <city>` | Current weather and forecast. |
| `!stocks <symbol or name>` | Stock quote (price, change, high/low). |
| `!crypto [symbol]` | Crypto prices (e.g. `!crypto btc`); no argument = top coins. |
| `!dice` | Roll a 6-sided die. |
| `!coin` | Flip a coin. |
| `!8ball <question>` | Magic 8-ball. |
| `!invite` | Bot invite link. |

---

## What Jarvis can do

- **AI chat** — Ask questions via `!jarvis` or `@Jarvis`; responses use GPT-4o-mini with conversation memory and optional tools.
- **Tools** — Jarvis can call web search (DuckDuckGo), weather (WeatherAPI), stocks (Finnhub), crypto (Messari), news (NewsAPI), and Wikipedia (define, summarize, search) when relevant.
- **Reply context** — Reply to any message and use `!jarvis` or `@Jarvis` to ask about that message.
- **Dedicated commands** — `!weather`, `!stocks`, and `!crypto` for quick lookups; news, define/summary/search are handled through Jarvis.
- **Greetings** — Responds to “hey jarvis”, “thanks jarvis”, “jarvis tell me a joke”, etc.

---

## Project members

- [Shaheriar Malik](https://github.com/shaheriar)
- [Ryan Giron](https://github.com/rgiron1)
- [Simraj Singh](https://github.com/simrajsingh)

---

## Inspiration

The bot is inspired by Iron Man’s AI Jarvis: an assistant that feels useful and a bit personal.

## How it’s built

Python with discord.py, OpenAI API (GPT + tool use), python-dotenv for config, and APIs for weather (WeatherAPI), stocks (Finnhub), news (NewsAPI), and Wikipedia. Web search via DuckDuckGo (ddgs); crypto via Messari.

## Challenges we ran into

Early versions were built while learning Python and wiring multiple APIs together. Later additions (GPT, tools, streaming, .env) required refactoring and clearer structure.

## What we learned

Using REST APIs, Discord’s bot API, and later OpenAI’s chat and function-calling APIs. Managing secrets with .env and keeping the codebase maintainable.

## What’s next

Ideas: games with Jarvis, more tools, and tighter integration with Discord (e.g. slash commands).
