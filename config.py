"""Centralized configuration: loads .env and exposes env vars. Import this first in bot.py."""
from dotenv import load_dotenv

load_dotenv()

import os


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


# Discord
DISCORD_TOKEN = _get("DISCORD_TOKEN")
DISCORD_GUILD = _get("DISCORD_GUILD")
BANNED_USER_IDS = set(
    x.strip() for x in os.getenv("BANNED_USER_IDS", "").split(",") if x.strip()
)

# APIs
WEATHER_API_KEY = _get("WEATHER_API_KEY")
FINNHUB_API_KEY = _get("FINNHUB_API_KEY")
NEWS_API_KEY = _get("NEWS_API_KEY")
OPENAI_API_KEY = _get("OPENAI_API_KEY")

# Invite link: optional BOT_CLIENT_ID env; default for backward compatibility
BOT_CLIENT_ID = _get("BOT_CLIENT_ID")
INVITE_LINK = (
    f"https://discord.com/api/oauth2/authorize?client_id={BOT_CLIENT_ID}&permissions=8&scope=bot"
)
