"""Stocks API service (Finnhub). Returns structured data for use by Jarvis tools and Discord embeds."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
import discord

logger = logging.getLogger(__name__)

BASE_URL = "https://finnhub.io/api/v1/"


def _range_to_unix(range_str: str) -> tuple[int, int] | None:
    """Map a simple range string to (from_ts, to_ts) in Unix seconds."""
    now = datetime.now(timezone.utc)
    range_str = (range_str or "").lower()
    if range_str == "1m":
        start = now - timedelta(days=30)
    elif range_str == "3m":
        start = now - timedelta(days=90)
    elif range_str == "6m":
        start = now - timedelta(days=180)
    elif range_str == "1y":
        start = now - timedelta(days=365)
    elif range_str == "ytd":
        start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    else:
        return None
    return int(start.timestamp()), int(now.timestamp())


async def get_stock_data(symbol: str, api_key: str, range: str | None = None) -> dict[str, Any]:
    """
    Fetch stock quote for a symbol or company name.

    If range is provided (e.g. '1m', '3m', '6m', '1y', 'ytd'), also fetch
    simple historical performance over that period and include it under
    the 'history' key.

    Returns structured dict on success, or {"error": "message"} on failure.
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

        data: dict[str, Any] = {
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
        # Optionally fetch simple historical candles for performance summary.
        ts_range = _range_to_unix(range) if range else None
        if ts_range:
            frm, to = ts_range
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{BASE_URL}stock/candle?symbol={s['symbol']}&resolution=D&from={frm}&to={to}{token}",
                        timeout=timeout,
                    ) as r:
                        candles = await r.json()
                if candles.get("s") == "ok" and candles.get("c"):
                    closes = candles["c"]
                    highs = candles.get("h") or closes
                    lows = candles.get("l") or closes
                    start_price = closes[0]
                    end_price = closes[-1]
                    change = end_price - start_price
                    change_pct = (change / start_price * 100) if start_price else 0
                    data["history"] = {
                        "range": range,
                        "from_ts": frm,
                        "to_ts": to,
                        "start_price": start_price,
                        "end_price": end_price,
                        "change": change,
                        "change_percent": change_pct,
                        "high": max(highs),
                        "low": min(lows),
                    }
            except Exception:
                logger.exception("Stock history lookup failed")
        return data
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
    base = (
        f"{data['description']} ({data['symbol']}): ${data['current']} "
        f"(change ${data['change']}, {data['change_percent']}%). "
        f"High ${data['high']}, Low ${data['low']}, Open ${data['open']}, Previous close ${data['previous_close']}."
    )
    hist = data.get("history")
    if hist:
        base += (
            f" Over the last {hist['range']}, it moved from ${round(hist['start_price'], 2)} "
            f"to ${round(hist['end_price'], 2)} ({round(hist['change_percent'], 2)}%)."
        )
    return base


def build_stock_embed(data: dict[str, Any]) -> discord.Embed:
    """Build Discord embed from stock service dict."""
    if "error" in data:
        return discord.Embed(title="Error", description=data["error"], color=0xE74C3C)
    title = f"Stock Information for {data['symbol']}"
    if data.get("history") and data["history"].get("range"):
        title += f" — last {data['history']['range']}"
    embed = discord.Embed(
        title=title,
    )
    embed.add_field(name="Name", value=data["description"], inline=False)
    embed.add_field(name="Current Price", value=f"${data['current']}", inline=False)
    embed.add_field(name="Change", value=f"${data['change']}", inline=True)
    embed.add_field(name="Percent Change", value=f"{data['change_percent']}%", inline=True)
    embed.add_field(name="High", value=f"${data['high']}", inline=True)
    embed.add_field(name="Low", value=f"${data['low']}", inline=True)
    embed.add_field(name="Open", value=f"${data['open']}", inline=True)
    embed.add_field(name="Previous Close Price", value=f"${data['previous_close']}", inline=True)

    embed.set_footer(text=datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
    hist = data.get("history")
    if hist:
        embed.add_field(
            name="Period Performance",
            value=(
                f"From ${round(hist['start_price'], 2)} to ${round(hist['end_price'], 2)} "
                f"({round(hist['change_percent'], 2)}%).\n"
                f"High: ${round(hist['high'], 2)}, Low: ${round(hist['low'], 2)}."
            ),
            inline=False,
        )
    if data.get("logo"):
        embed.set_thumbnail(url=data["logo"])
    return embed
