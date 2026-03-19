"""Web search service (DuckDuckGo). Returns formatted text for Jarvis."""
import logging

from ddgs import DDGS

from services import web_fetch as web_fetch_svc

logger = logging.getLogger(__name__)


def web_search(
    query: str, max_results: int = 5, max_context_chars: int = 2000
) -> str:
    """
    Run DuckDuckGo search and return formatted snippets as a single string.
    Used by Jarvis tool. Sync; run via asyncio.to_thread from async code.
    """
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
        logger.exception("Web search error")
        return f"[Web search failed: {e}]"


async def web_search_deep(query: str, *, max_results: int = 5, fetch_top_n: int = 3) -> dict:
    """Search first, then fetch top result pages for deeper context."""
    try:
        results = list(DDGS().text(query, max_results=max_results) or [])
    except Exception as exc:
        logger.exception("Deep web search failed")
        return {"error": f"Search failed: {exc}", "query": query, "items": []}

    items: list[dict] = []
    for idx, result in enumerate(results[:max_results], 1):
        href = result.get("href", "")
        title = result.get("title", "")
        snippet = (result.get("body") or "")[:300]
        item = {"rank": idx, "url": href, "title": title, "snippet": snippet}
        if idx <= fetch_top_n and href:
            fetched = await web_fetch_svc.fetch_url_text(href)
            item["fetched_title"] = fetched.get("title", "")
            item["excerpt"] = (fetched.get("content", "") or "")[:1000]
            if "error" in fetched:
                item["fetch_error"] = fetched["error"]
        items.append(item)
    return {"query": query, "items": items}


def format_deep_search_as_text(data: dict) -> str:
    if "error" in data:
        return f"[web_search_deep error] {data.get('error')}"
    items = data.get("items") or []
    if not items:
        return "No results found."
    lines: list[str] = []
    for item in items:
        lines.append(f"[{item.get('rank')}] {item.get('title')}\nSource: {item.get('url')}")
        excerpt = item.get("excerpt") or item.get("snippet") or ""
        if excerpt:
            lines.append(excerpt[:400])
        fetch_error = item.get("fetch_error")
        if fetch_error:
            lines.append(f"(fetch note: {fetch_error})")
        lines.append("")
    return "\n".join(lines).strip()
