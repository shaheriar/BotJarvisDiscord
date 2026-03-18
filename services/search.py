"""Web search service (DuckDuckGo). Returns formatted text for Jarvis."""
import logging

from ddgs import DDGS

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
