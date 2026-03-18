"""Crypto API service (Messari). Returns structured data for use by Jarvis tools and Discord embeds."""
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

BASE_URL = "https://data.messari.io/api/v1/assets"


async def get_crypto_data(symbol: str | None) -> dict[str, Any]:
    """
    Fetch crypto data. If symbol is empty/None, returns top coins list.
    Returns structured dict on success, or {"error": "message"} on failure.
    """
    symbol = (symbol or "").strip() if symbol is not None else ""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        if not symbol:
            async with aiohttp.ClientSession() as session:
                async with session.get(BASE_URL, timeout=timeout) as r:
                    data = await r.json()
            coins = []
            for x in data.get("data", [])[:10]:
                coins.append({
                    "name": x["name"],
                    "symbol": x["symbol"],
                    "price_usd": x["metrics"]["market_data"]["price_usd"],
                })
            return {"coins": coins}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/{symbol.lower()}/metrics", timeout=timeout) as r:
                data = await r.json()
        d = data["data"]
        m = d["market_data"]
        return {
            "name": d["name"],
            "symbol": d["symbol"],
            "price_usd": m["price_usd"],
            "ohlcv_1h": m.get("ohlcv_last_1_hour"),
            "ohlcv_24h": m.get("ohlcv_last_24_hour"),
        }
    except aiohttp.ClientError as e:
        logger.exception("Crypto API request failed")
        return {"error": str(e)}
    except Exception as e:
        logger.exception("Crypto lookup failed")
        return {"error": str(e)}


def format_crypto_as_text(data: dict[str, Any]) -> str:
    """Format crypto data as plain text for Jarvis."""
    if "error" in data:
        return f"Crypto lookup failed: {data['error']}"
    if "coins" in data:
        lines = [
            f"{c['name']} ({c['symbol']}): ${round(c['price_usd'], 5)}"
            for c in data["coins"]
        ]
        return "\n".join(lines) if lines else "No crypto data."
    m = data.get("ohlcv_24h") or {}
    return (
        f"{data['name']} ({data['symbol']}): ${round(data['price_usd'], 5)}. "
        f"24h: O ${round(m.get('open', 0), 5)} H ${round(m.get('high', 0), 5)} "
        f"L ${round(m.get('low', 0), 5)} C ${round(m.get('close', 0), 5)}."
    )
