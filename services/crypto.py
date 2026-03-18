"""Crypto API service (CoinGecko). Returns structured data for use by Jarvis tools and Discord embeds."""
import logging
from typing import Any

import aiohttp
import discord

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Map common symbols to canonical CoinGecko coin id (avoids picking wrapped/duplicate tokens).
CANONICAL_IDS: dict[str, str] = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "usdt": "tether",
    "usdc": "usd-coin",
    "bnb": "binancecoin",
    "sol": "solana",
    "xrp": "ripple",
    "doge": "dogecoin",
    "ada": "cardano",
    "avax": "avalanche-2",
    "link": "chainlink",
    "dot": "polkadot",
    "matic": "matic-network",
    "shib": "shiba-inu",
    "ltc": "litecoin",
    "uni": "uniswap",
    "atom": "cosmos",
    "xlm": "stellar",
}


async def get_crypto_data(symbol: str | None, range: str | None = None, api_key: str | None = None) -> dict[str, Any]:
    """
    Fetch crypto data using CoinGecko.

    - If symbol is empty/None: returns top coins list by market cap (limited to 10).
    - If symbol provided: returns current price and 24h change for that asset.

    Note: CoinGecko's free API does not require an API key and this implementation
    currently ignores the range parameter (only stocks support range performance).

    Returns structured dict on success, or {"error": "message"} on failure.
    """
    symbol = (symbol or "").strip().lower() if symbol is not None else ""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        headers: dict[str, str] = {}
        if api_key:
            # CoinGecko demo/pro key header per docs
            headers["x-cg-demo-api-key"] = api_key

        # Top coins list
        if not symbol:
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": "10",
                "page": "1",
                "sparkline": "false",
            }
            async with aiohttp.ClientSession(headers=headers or None) as session:
                async with session.get(f"{COINGECKO_BASE}/coins/markets", params=params, timeout=timeout) as r:
                    data = await r.json()
            coins = []
            for x in data or []:
                coins.append({
                    "name": x.get("name"),
                    "symbol": x.get("symbol", "").upper(),
                    "price_usd": x.get("current_price"),
                })
            if not coins:
                return {"error": "No crypto data returned from CoinGecko."}
            return {"coins": coins}

        # Single asset: resolve symbol to CoinGecko id (prefer canonical to avoid wrong token)
        matched_id = CANONICAL_IDS.get(symbol)
        if not matched_id:
            async with aiohttp.ClientSession(headers=headers or None) as session:
                async with session.get(f"{COINGECKO_BASE}/coins/list", timeout=timeout) as r:
                    listing = await r.json()
            for coin in listing or []:
                if coin.get("symbol", "").lower() == symbol:
                    matched_id = coin.get("id")
                    break
            if not matched_id:
                for coin in listing or []:
                    if coin.get("id", "").lower() == symbol:
                        matched_id = coin.get("id")
                        break
        if not matched_id:
            return {"error": f"No crypto asset found for symbol: {symbol}"}

        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        }
        async with aiohttp.ClientSession(headers=headers or None) as session:
            async with session.get(f"{COINGECKO_BASE}/coins/{matched_id}", params=params, timeout=timeout) as r:
                detail = await r.json()
        market = (detail.get("market_data") or {})
        current_price = (market.get("current_price") or {}).get("usd")
        change_24h = market.get("price_change_24h_in_currency", {}).get("usd") or market.get("price_change_24h")
        change_pct_24h = (market.get("price_change_percentage_24h_in_currency") or {}).get("usd") or market.get("price_change_percentage_24h")

        return {
            "name": detail.get("name"),
            "symbol": detail.get("symbol", "").upper(),
            "price_usd": current_price,
            "change_24h": change_24h,
            "change_pct_24h": change_pct_24h,
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
    base = f"{data['name']} ({data['symbol']}): ${round(data['price_usd'], 5)}."
    if data.get("change_24h") is not None:
        base += f" 24h change: ${round(data['change_24h'], 5)}"
    if data.get("change_pct_24h") is not None:
        base += f" ({round(data['change_pct_24h'], 2)}%)."
    return base


def build_crypto_embed(data: dict[str, Any]) -> discord.Embed:
    """Build Discord embed from crypto service dict."""
    if "error" in data:
        return discord.Embed(title="Error", description=data["error"], color=0xE74C3C)
    from datetime import datetime as _dt

    if "coins" in data:
        embed = discord.Embed(title="Cryptocurrency Market Today")
        for c in data["coins"]:
            embed.add_field(
                name=f"{c['name']} ({c['symbol']})",
                value=f"${round(c['price_usd'], 5)}",
                inline=True,
            )
        embed.set_footer(text=_dt.now().strftime("%m/%d/%Y, %H:%M:%S"))
        return embed
    # Single coin
    name = data["name"]
    symbol = data["symbol"]
    price = data["price_usd"]
    embed = discord.Embed(title=f"Market data for {name} ({symbol})")
    embed.add_field(name="Price", value=f"${round(price, 5)}", inline=False)
    if data.get("change_24h") is not None:
        embed.add_field(name="24h Change", value=f"${round(data['change_24h'], 5)}", inline=True)
    if data.get("change_pct_24h") is not None:
        embed.add_field(name="24h Change %", value=f"{round(data['change_pct_24h'], 2)}%", inline=True)
    embed.set_footer(text=_dt.now().strftime("%m/%d/%Y, %H:%M:%S"))
    return embed
