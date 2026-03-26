"""Stocks API service (Finnhub + Alpha Vantage movers).

Returns structured data for use by Jarvis tools and Discord embeds.
"""
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any

import aiohttp
import discord

logger = logging.getLogger(__name__)

BASE_URL = "https://finnhub.io/api/v1/"
ALPHAVANTAGE_BASE_URL = "https://www.alphavantage.co/query"
ALPHAVANTAGE_TOP_GAINERS_LOSERS_FUNCTION = "TOP_GAINERS_LOSERS"


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


def _to_float(value: Any) -> float | None:
    """Best-effort conversion to float (handles % signs and commas)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    s = s.replace(",", "").replace("%", "")
    try:
        return float(s)
    except Exception:
        return None


def _extract_first_list(payload: dict[str, Any], *, required_predicate) -> list[dict[str, Any]]:
    for _, v in payload.items():
        if not isinstance(v, list) or not v:
            continue
        first = v[0]
        if not isinstance(first, dict):
            continue
        if required_predicate(first):
            # Filter to dict-only items; some APIs can include stray values.
            return [x for x in v if isinstance(x, dict)]
    return []


async def get_stock_movers(
    *,
    api_key: str,
    direction: str = "both",
    top_n: int = 5,
    region: str = "US",
) -> dict[str, Any]:
    """
    Get top stock movers (gainers & losers) for US stocks.

    Uses Alpha Vantage `TOP_GAINERS_LOSERS` endpoint to discover movers, then
    normalizes the results into a format suitable for Discord embeds.
    """
    if not (api_key and api_key.strip()):
        return {"error": "Alpha Vantage API is not configured (missing ALPHAVANTAGE_API_KEY)."}

    direction = (direction or "both").lower().strip()
    if direction not in ("gainers", "losers", "both"):
        direction = "both"

    try:
        top_n_i = int(top_n)
    except Exception:
        top_n_i = 5
    top_n_i = max(1, min(top_n_i, 25))

    region = (region or "US").upper().strip()
    if region != "US":
        region = "US"

    timeout = aiohttp.ClientTimeout(total=10)
    params = {
        "function": ALPHAVANTAGE_TOP_GAINERS_LOSERS_FUNCTION,
        "apikey": api_key,
    }

    url = ALPHAVANTAGE_BASE_URL
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as r:
                data = await r.json(content_type=None)
                # Debug: show the raw movers API payload in console logs.
                # (This contains only public market data, but can be noisy.)
                print("[StockMovers] AlphaVantage TOP_GAINERS_LOSERS response:", data)
                if not isinstance(data, dict):
                    return {"error": "Alpha Vantage returned unexpected response format."}

    except aiohttp.ClientError as e:
        logger.exception("AlphaVantage movers request failed")
        return {"error": str(e)}
    except Exception as e:
        logger.exception("AlphaVantage movers lookup failed")
        return {"error": str(e)}

    if "error" in data:
        return {"error": str(data.get("error"))}
    if "Note" in data:
        # Alpha Vantage rate-limit responses typically use "Note".
        return {"error": str(data.get("Note"))}

    def _has_ticker_and_change(entry: dict[str, Any]) -> bool:
        # Typical Alpha Vantage movers rows include:
        # - ticker
        # - price
        # - changesPercentage
        # - change
        ticker = entry.get("ticker") or entry.get("symbol") or entry.get("Symbol")
        cp = (
            entry.get("change_percentage")
            or entry.get("changesPercentage")
            or entry.get("changes_percentage")
            or entry.get("percentChange")
        )
        return bool(ticker) and (cp is not None)

    def _is_gainers_row(entry: dict[str, Any]) -> bool:
        # Gain rows are usually positive.
        cp = _to_float(
            entry.get("change_percentage")
            or entry.get("changesPercentage")
            or entry.get("percentChange")
        )
        return cp is not None and cp >= 0

    # Pull candidate lists from the payload. Alpha Vantage typically provides
    # `top_gainers`, `top_losers`, and `most_active`, but we don't rely on
    # exact key names to be robust.
    gainers_raw = (
        _extract_first_list(data, required_predicate=lambda e: _has_ticker_and_change(e) and _is_gainers_row(e))
        if direction in ("gainers", "both")
        else []
    )
    losers_raw = (
        _extract_first_list(data, required_predicate=lambda e: _has_ticker_and_change(e) and not _is_gainers_row(e))
        if direction in ("losers", "both")
        else []
    )

    # Normalize + sort (even if Alpha Vantage already returns top N sorted).
    def _normalize(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for it in items:
            sym = (it.get("ticker") or it.get("symbol") or "").strip().upper()
            if not sym:
                continue
            price = _to_float(it.get("price") or it.get("current") or it.get("lastPrice"))
            chg_pct = _to_float(
                it.get("change_percentage")
                or it.get("changesPercentage")
                or it.get("changes_percentage")
                or it.get("percentChange")
            )
            chg = _to_float(it.get("change_amount") or it.get("change"))
            if chg_pct is None:
                continue
            out.append(
                {
                    "symbol": sym,
                    "current": price,
                    "change": chg,
                    "change_percent": chg_pct,
                }
            )
        return out

    gainers = sorted(
        _normalize(gainers_raw), key=lambda x: float(x.get("change_percent") or 0), reverse=True
    )[:top_n_i]
    losers = sorted(
        _normalize(losers_raw), key=lambda x: float(x.get("change_percent") or 0)
    )[:top_n_i]

    # If the direction requested only one side, still return both keys so the embed is predictable.
    return {
        "kind": "movers",
        "region": region,
        "direction": direction,
        "top_n": top_n_i,
        "source_metadata": data.get("metadata"),
        "last_updated": data.get("last_updated"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "gainers": gainers if direction in ("gainers", "both") else [],
        "losers": losers if direction in ("losers", "both") else [],
    }


def format_stock_movers_as_text(data: dict[str, Any]) -> str:
    """Format movers data as plain text for Jarvis tool context."""
    if "error" in data:
        return f"Stock movers lookup failed: {data['error']}"
    if data.get("kind") != "movers":
        return "Stock movers lookup failed: unexpected payload."

    top_n = int(data.get("top_n") or 5)
    region = data.get("region") or "US"
    last_updated = data.get("last_updated") or ""

    gainers = data.get("gainers") or []
    losers = data.get("losers") or []

    gainers_lines = [
        _format_movers_row(i, it)
        for i, it in enumerate(gainers[:top_n], start=1)
    ] or ["(none)"]
    losers_lines = [
        _format_movers_row(i, it)
        for i, it in enumerate(losers[:top_n], start=1)
    ] or ["(none)"]

    header = f"US Stock Movers (Top {top_n} Gainers & Losers)"
    if last_updated:
        header += f" | Last updated: {last_updated}"

    return (
        f"{header}\n\n"
        f"Top Gainers:\n"
        f"```txt\n{chr(10).join(gainers_lines)}\n```\n\n"
        f"Top Losers:\n"
        f"```txt\n{chr(10).join(losers_lines)}\n```"
    )

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


def _fmt_pct(value: Any) -> str:
    v = _to_float(value)
    if v is None:
        return str(value)
    sign = "+" if v >= 0 else "-"
    return f"{sign}{abs(v):.2f}%"


def _fmt_money(value: Any) -> str:
    v = _to_float(value)
    if v is None:
        return ""
    decimals = 4 if abs(v) < 1 else 2
    return f"${v:.{decimals}f}"


def _fmt_money_signed(value: Any) -> str:
    v = _to_float(value)
    if v is None:
        return str(value)
    sign = "+" if v >= 0 else "-"
    return f"{sign}{_fmt_money(abs(v))}"


def _code_block(lines: list[str]) -> str:
    body = "\n".join(lines) if lines else "(none)"
    return f"```txt\n{body}\n```"


def _format_movers_row(rank: int, it: dict[str, Any]) -> str:
    sym = (it.get("symbol") or "").strip()
    current = _to_float(it.get("current"))
    change = _to_float(it.get("change"))
    cp = _to_float(it.get("change_percent"))
    if current is None or change is None or cp is None:
        return f"{rank}. {sym}"

    # Alpha Vantage gives `price` and `change_amount` (+/- dollars). Compute the before price.
    before = current - change

    # Fixed-width-ish columns so the monospace code block aligns nicely.
    # Example columns:
    #   rank, symbol, % change, $ change, $ before -> $ after
    pct = _fmt_pct(cp)
    chg = _fmt_money_signed(change)
    before_s = _fmt_money(before)
    after_s = _fmt_money(current)

    # Column widths tuned to match the user's requested layout.
    # Note: before_s is right-aligned to keep the same "gap" before "$X.XX" seen in examples.
    # Layout targets (example):
    #   " 1. UGRO       +416.95%      +$29.27      $7.02 ->     $36.29"
    return f"{rank:>2}. {sym:<11}{pct}{chg:>14}{before_s:>12} -> {after_s:>12}"


def _parse_last_updated(value: Any) -> datetime | None:
    """Parse Alpha Vantage 'last_updated' into an embed timestamp when possible."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None

    # Best effort: ISO-ish first.
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass

    # Alpha Vantage / our text formatting may include a timezone name at the end,
    # e.g. "2026-03-25 16:15:57 US/Eastern".
    if " " in s:
        dt_part, tz_part = s.rsplit(" ", 1)
        try:
            tz = ZoneInfo(tz_part)
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %I:%M:%S %p"):
                try:
                    dt = datetime.strptime(dt_part, fmt)
                    return dt.replace(tzinfo=tz)
                except ValueError:
                    continue
        except Exception:
            pass

    # Common Alpha Vantage formats (no timezone).
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %I:%M:%S %p"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def build_stock_embed(data: dict[str, Any]) -> discord.Embed:
    """Build Discord embed from stock service dict."""
    if "error" in data:
        return discord.Embed(title="Error", description=data["error"], color=0xE74C3C)

    if data.get("kind") == "movers":
        top_n = int(data.get("top_n") or 5)
        region = data.get("region") or "US"
        gainers = data.get("gainers") or []
        losers = data.get("losers") or []

        title = f"US Stock Movers (Top {top_n} Gainers & Losers)"
        embed = discord.Embed(title=title, description=data.get("source_metadata") or "Top percent movers.", color=0x2E86C1)

        ts = _parse_last_updated(data.get("last_updated"))
        if ts:
            embed.timestamp = ts
        else:
            # Fallback: still show the raw last-updated string if parsing fails.
            last_updated = data.get("last_updated") or ""
            if last_updated:
                embed.set_footer(text=f"Last updated: {last_updated}")

        def _format_category_lines(emoji: str, items: list[dict[str, Any]]) -> list[str]:
            rows: list[tuple[str, str, str, str, str]] = []
            for it in items:
                sym = (it.get("symbol") or "").strip().upper()
                current = _to_float(it.get("current"))
                change = _to_float(it.get("change"))
                cp = _to_float(it.get("change_percent"))
                if not sym or current is None or change is None or cp is None:
                    continue
                before = current - change
                pct_s = _fmt_pct(cp)
                chg_s = _fmt_money_signed(change)
                before_s = _fmt_money(before)
                after_s = _fmt_money(current)
                rows.append((sym, pct_s, chg_s, before_s, after_s))

            if not rows:
                return []

            max_sym = max(len(r[0]) for r in rows)
            max_pct = max(len(r[1]) for r in rows)
            max_chg = max(len(r[2]) for r in rows)
            max_before = max(len(r[3]) for r in rows)
            max_after = max(len(r[4]) for r in rows)

            out: list[str] = []
            for sym, pct_s, chg_s, before_s, after_s in rows:
                out.append(
                    f"{emoji} {sym:<{max_sym}}:"
                    f" {pct_s:>{max_pct}} |"
                    f" {chg_s:>{max_chg}} |"
                    f" {before_s:>{max_before}} ->"
                    f" {after_s:>{max_after}}"
                )
            return out

        gainers_lines = _format_category_lines("🟢", gainers[:top_n] or [])
        losers_lines = _format_category_lines("🔴", losers[:top_n] or [])

        embed.add_field(
            name=f"Top Gainers ({region})",
            value=_code_block(gainers_lines) if gainers_lines else "(none)",
            inline=False,
        )
        embed.add_field(
            name=f"Top Losers ({region})",
            value=_code_block(losers_lines) if losers_lines else "(none)",
            inline=False,
        )

        return embed

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
