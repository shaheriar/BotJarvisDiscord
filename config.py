"""Centralized configuration: loads .env and exposes env vars. Import this first in bot.py."""
from dotenv import load_dotenv

load_dotenv()

import os


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()

def _get_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


def _get_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(float(raw.strip()))
    except ValueError:
        return default


def _get_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    return default


# Discord
DISCORD_TOKEN = _get("DISCORD_TOKEN")
_DISCORD_GUILD_RAW = _get("DISCORD_GUILD")
try:
    DISCORD_GUILD = int(_DISCORD_GUILD_RAW) if _DISCORD_GUILD_RAW else None
except ValueError:
    DISCORD_GUILD = None
BANNED_USER_IDS = set(
    x.strip() for x in os.getenv("BANNED_USER_IDS", "").split(",") if x.strip()
)

# APIs
WEATHER_API_KEY = _get("WEATHER_API_KEY")
FINNHUB_API_KEY = _get("FINNHUB_API_KEY")
ALPHAVANTAGE_API_KEY = _get("ALPHAVANTAGE_API_KEY")
NEWS_API_KEY = _get("NEWS_API_KEY")
OPENAI_API_KEY = _get("OPENAI_API_KEY")
COINGECKO_API_KEY = _get("COINGECKO_API_KEY")
DEEPL_API_KEY = _get("DEEPL_API_KEY")

# Invite link: optional BOT_CLIENT_ID env; default for backward compatibility
BOT_CLIENT_ID = _get("BOT_CLIENT_ID")
INVITE_LINK = (
    f"https://discord.com/api/oauth2/authorize?client_id={BOT_CLIENT_ID}&permissions=8&scope=bot"
)

# Jarvis LLM tuning
# These are env-overridable so you can tune quality/cost without redeploying code.
JARVIS_MODEL = _get("JARVIS_MODEL", "gpt-4o-mini")
JARVIS_SUMMARY_MODEL = _get("JARVIS_SUMMARY_MODEL", JARVIS_MODEL)
JARVIS_TOOL_TEMPERATURE = _get_float("JARVIS_TOOL_TEMPERATURE", 0.1)
JARVIS_RESPONSE_TEMPERATURE = _get_float("JARVIS_RESPONSE_TEMPERATURE", 0.5)
JARVIS_TOOL_CALL_MAX_TOKENS = _get_int("JARVIS_TOOL_CALL_MAX_TOKENS", 256)
JARVIS_TOOL_REQUERY_MAX_TOKENS = _get_int("JARVIS_TOOL_REQUERY_MAX_TOKENS", 512)
JARVIS_FINAL_RESPONSE_MAX_TOKENS = _get_int("JARVIS_FINAL_RESPONSE_MAX_TOKENS", 640)
JARVIS_NEWS_SUMMARY_MODEL = _get("JARVIS_NEWS_SUMMARY_MODEL", JARVIS_MODEL)
JARVIS_NEWS_SUMMARY_MAX_TOKENS = _get_int("JARVIS_NEWS_SUMMARY_MAX_TOKENS", 1000)
JARVIS_NEWS_SUMMARY_TEMPERATURE = _get_float("JARVIS_NEWS_SUMMARY_TEMPERATURE", 0.22)
JARVIS_NEWS_FETCH_PAGE_SIZE = _get_int("JARVIS_NEWS_FETCH_PAGE_SIZE", 20)
JARVIS_MAX_AGENT_ITERATIONS = _get_int("JARVIS_MAX_AGENT_ITERATIONS", 5)
JARVIS_MAX_RESEARCH_CHARS = _get_int("JARVIS_MAX_RESEARCH_CHARS", 4000)
JARVIS_SELF_CRITIQUE = _get_bool("JARVIS_SELF_CRITIQUE", False)
JARVIS_MEMORY_DB_PATH = _get("JARVIS_MEMORY_DB_PATH", "data/jarvis.db")

# Web fetch/browser controls (Pi-friendly defaults)
WEB_FETCH_MAX_CHARS = _get_int("WEB_FETCH_MAX_CHARS", 3000)
WEB_FETCH_TIMEOUT = _get_int("WEB_FETCH_TIMEOUT", 10)
WEB_FETCH_MAX_BYTES = _get_int("WEB_FETCH_MAX_BYTES", 2_000_000)
WEB_FETCH_DENYLIST = _get("WEB_FETCH_DENYLIST", "")
BROWSER_ENABLED = _get_bool("BROWSER_ENABLED", False)
PLAYWRIGHT_HEADLESS = _get_bool("PLAYWRIGHT_HEADLESS", True)

# Daily Top Movers scheduler
TOP_MOVERS_DAILY_TIME_UTC = _get("TOP_MOVERS_DAILY_TIME_UTC", "09:00")  # HH:MM in UTC
TOP_MOVERS_TOP_N = _get_int("TOP_MOVERS_TOP_N", 5)
TOP_MOVERS_REGION = _get("TOP_MOVERS_REGION", "US")
