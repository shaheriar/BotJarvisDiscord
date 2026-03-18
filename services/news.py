"""News API service. Returns structured data for use by Jarvis tools and Discord embeds."""
import logging
from typing import Any
from urllib.parse import quote

import aiohttp

logger = logging.getLogger(__name__)


async def get_news_data(query: str | None, api_key: str) -> dict[str, Any]:
    """
    Fetch headline news. Optional topic; empty query = top US headlines.
    Returns {"articles": [...]} on success, or {"error": "message"} on failure.
    """
    if not (api_key and api_key.strip()):
        return {"error": "News API is not configured (missing NEWS_API_KEY)."}
    try:
        if query and query.strip():
            url = (
                f"https://newsapi.org/v2/top-headlines?language=en&q={quote(query.strip())}"
                f"&pageSize=5&apiKey={api_key}"
            )
        else:
            url = f"https://newsapi.org/v2/top-headlines?country=us&pageSize=5&apiKey={api_key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
        if data.get("status") == "error":
            return {"error": data.get("message", "Unknown error")}
        articles = data.get("articles") or []
        if not articles:
            return {"error": "No news articles found for that topic."}
        out = []
        for a in articles[:5]:
            out.append({
                "title": (a.get("title") or "").strip() or "(No title)",
                "description": (a.get("description") or "").strip() or "",
                "url": (a.get("url") or "").strip() or "",
                "source": (a.get("source") or {}).get("name", "Unknown"),
            })
        return {"articles": out}
    except aiohttp.ClientError as e:
        logger.exception("News API request failed")
        return {"error": str(e)}
    except Exception as e:
        logger.exception("News lookup failed")
        return {"error": str(e)}


def format_news_as_text(data: dict[str, Any]) -> str:
    """Format news data as plain text for Jarvis."""
    if "error" in data:
        return f"News API error: {data['error']}"
    lines = []
    for i, a in enumerate(data["articles"], 1):
        block = f"[{i}] {a['title']} — {a['source']}"
        if a["description"]:
            block += f"\n{a['description'][:300]}{'...' if len(a['description']) > 300 else ''}"
        if a["url"]:
            block += f"\n{a['url']}"
        lines.append(block)
    return "\n\n".join(lines)
