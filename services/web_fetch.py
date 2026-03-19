"""Lightweight web fetching and content extraction."""
from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

import aiohttp

import config

logger = logging.getLogger(__name__)


def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def _domain_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    deny = {d.strip().lower() for d in config.WEB_FETCH_DENYLIST.split(",") if d.strip()}
    return host not in deny


async def fetch_url_text(url: str, *, max_chars: int | None = None) -> dict:
    """Fetch URL and return title/text/source metadata."""
    try:
        import trafilatura  # Local import so missing optional deps don't crash bot startup.
    except Exception as exc:
        return {"error": f"Web extraction unavailable: {exc}"}

    max_chars = max_chars or config.WEB_FETCH_MAX_CHARS
    url = _normalize_url(url)
    if not url:
        return {"error": "Empty URL."}
    if not _domain_allowed(url):
        return {"error": "Domain is blocked by policy.", "url": url}

    timeout = aiohttp.ClientTimeout(total=max(1, config.WEB_FETCH_TIMEOUT))
    headers = {"User-Agent": "JarvisBot/1.0 (+discord assistant)"}
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as resp:
                content_type = (resp.headers.get("Content-Type") or "").lower()
                if "text/html" not in content_type and "text/plain" not in content_type:
                    return {"error": f"Unsupported content type: {content_type}", "url": str(resp.url)}

                body = await resp.read()
                if len(body) > config.WEB_FETCH_MAX_BYTES:
                    return {"error": "Response body too large.", "url": str(resp.url)}
                text = body.decode("utf-8", errors="replace")
                final_url = str(resp.url)
    except asyncio.TimeoutError:
        return {"error": "Request timed out.", "url": url}
    except Exception as exc:
        logger.exception("web_fetch_failed")
        return {"error": f"Fetch failed: {exc}", "url": url}

    extracted = trafilatura.extract(
        text,
        url=final_url,
        include_comments=False,
        include_tables=False,
    )
    cleaned = (extracted or "").strip()
    if not cleaned:
        cleaned = trafilatura.extract(text, url=final_url, favor_precision=False, favor_recall=True) or ""
        cleaned = cleaned.strip()
    if not cleaned:
        cleaned = text[:max_chars]

    metadata = trafilatura.extract_metadata(text)
    title = metadata.title if metadata else ""
    return {
        "url": final_url,
        "title": title,
        "content": cleaned[:max_chars],
    }


def format_fetch_result(data: dict) -> str:
    if "error" in data:
        return f"[web_fetch error] {data.get('error')}"
    title = data.get("title") or "(untitled)"
    url = data.get("url") or ""
    content = (data.get("content") or "").strip()
    return f"Title: {title}\nURL: {url}\n\n{content}"
