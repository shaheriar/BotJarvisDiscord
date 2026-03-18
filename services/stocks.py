"""Stocks API service (Finnhub). Returns structured data for use by Jarvis tools and Discord embeds."""
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

BASE_URL = "https://finnhub.io/api/v1/"


async def get_stock_data(symbol: str, api_key: str) -> dict[str, Any]:
    """
    Fetch stock quote for a symbol or company name. Returns structured dict on success,
    or {"error": "message"} on failure.
    """
    if not (api_key and api_key.strip()):
        return {"error": "Finnhub API is not configured (missing FINNHUB_API_KEY)."}
    symbol = (symbol or "").strip()
    if not symbol:
        return {"error": "Stock symbol or company name is required."}
    try:
        token = f"&token={api_key}"
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}search?q={symbol}{token}", timeout=timeout) as r:
                search = await r.json()
        if not search.get("result"):
            return {"error": f"No stock found for symbol: {symbol}"}
        s = search["result"][0]
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}quote?symbol={s['symbol']}{token}", timeout=timeout) as r:
                info = await r.json()
        logo = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{BASE_URL}stock/profile2?symbol={s['symbol']}{token}", timeout=timeout
                ) as r:
                    profile = await r.json()
            logo = profile.get("logo") or None
        except Exception:
            pass
        return {
            "description": s["description"],
            "symbol": s["symbol"],
            "current": info["c"],
            "change": info["d"],
            "change_percent": info["dp"],
            "high": info["h"],
            "low": info["l"],
            "open": info["o"],
            "previous_close": info["pc"],
            "logo": logo,
        }
    except aiohttp.ClientError as e:
        logger.exception("Stocks API request failed")
        return {"error": str(e)}
    except Exception as e:
        logger.exception("Stock lookup failed")
        return {"error": str(e)}


def format_stock_as_text(data: dict[str, Any]) -> str:
    """Format stock data as plain text for Jarvis."""
    if "error" in data:
        return f"Stock lookup failed: {data['error']}"
    return (
        f"{data['description']} ({data['symbol']}): ${data['current']} "
        f"(change ${data['change']}, {data['change_percent']}%). "
        f"High ${data['high']}, Low ${data['low']}, Open ${data['open']}, Previous close ${data['previous_close']}."
    )
