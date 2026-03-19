"""DuckDuckGo fallback for NewsAPI failures.

When NewsAPI errors/returns empty, Jarvis uses a secondary search with
additional site constraints and heuristic ranking to produce a short
set of recent snippets.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone

from services import search as search_svc
from services.news import _blurb_preview, _effective_article_blurb

from cogs.tool_defs import _sanitize_assistant_output


async def news_search_fallback(query: str) -> str | None:
    """Fallback when NewsAPI fails.

    Returns a formatted text response suitable for sending in Discord, or
    `None` when no usable snippets are found.
    """

    original_q = (query or "").strip()
    if not original_q:
        return None

    # Extract a clean topic from the question text.
    q_lower = original_q.lower()
    if "user question:" in q_lower:
        q_lower = original_q.split("User question:", 1)[-1].strip().lower()

    m = re.search(r"(?i)\b(?:in|about|for)\b\s+(.+)$", original_q)
    topic = (m.group(1) if m else original_q).strip()

    # Remove filler words/phrasing.
    topic = re.sub(
        r"(?i)\b(today|todays|latest|news|headlines|current events|show me|breaking)\b",
        " ",
        topic,
    )
    topic = " ".join(topic.split())
    topic = topic[:80]

    # Significant words from the topic for generic relevance scoring (not geo-specific).
    _topic_tokens = [
        t
        for t in re.findall(r"[a-z0-9]+", topic.lower())
        if len(t) >= 4
    ][:12]

    current_year = str(datetime.now(timezone.utc).year)

    # Force publisher-level intent so we don't pull "breaking news headlines" hubs.
    fallback_q = (
        f"{topic} latest news {current_year} "
        "(site:reuters.com OR site:apnews.com OR site:bbc.com OR site:aljazeera.com) "
        "-site:groundnews.com -site:wikipedia.org -site:britannica.com"
    ).strip()

    try:
        # Request more snippets than we expect to show, since we'll rank/filter.
        search_text = await asyncio.to_thread(search_svc.web_search, fallback_q, 8, 3500)
    except Exception:
        search_text = ""

    # Keep links intact for the fallback.
    search_text = _sanitize_assistant_output(search_text, remove_urls=False)
    if not search_text:
        return None

    blocks = [b.strip() for b in search_text.split("\n\n") if b.strip()]

    def is_low_quality(block: str) -> bool:
        # Index-like phrases; these snippets often come from hub pages.
        patterns = [
            r"(?i)\bbreaking news headlines\b",
            r"(?i)\blatest news headlines\b",
            r"(?i)\ball the latest and breaking news\b",
            r"(?i)\bread latest .* news\b",
            r"(?i)\bbreaking news\b\s+\bheadlines\b",
        ]
        return any(re.search(p, block) for p in patterns)

    def score_block(block: str) -> int:
        score = 0
        # Prefer explicit recency indicators.
        if re.search(r"(?i)\b\d+\s+(minutes|minute|hours|hour|days|day)\s+ago\b", block):
            score += 6
        # Prefer recent years.
        if re.search(r"\b(2026|2025)\b", block):
            score += 3
        # Penalize generic hub terms.
        if re.search(r"(?i)\b(headlines|breaking news|latest news)\b", block):
            score -= 2
        # Prefer specificity: numbers.
        if re.search(r"\d", block):
            score += 1
        # Prefer overlap with the user's topic (whole-token match).
        if _topic_tokens:
            overlap = sum(
                1
                for t in _topic_tokens
                if re.search(rf"(?i)(?<!\w){re.escape(t)}(?!\w)", block)
            )
            score += min(overlap * 2, 8)
        return score

    # Filter + dedupe by "title-ish" first line.
    excluded_domains = ("groundnews.com", "wikipedia.org", "britannica.com")
    seen: set[str] = set()
    candidates: list[tuple[int, str]] = []

    for b in blocks:
        if is_low_quality(b):
            continue

        src_match = re.search(r"(?im)^Source:\s*(\S+)\s*$", b)
        href = src_match.group(1) if src_match else ""
        href_l = href.lower()
        if any(dom in href_l for dom in excluded_domains):
            continue

        title_match = re.match(r"(?m)^\[\d+\]\s*(.+)$", b)
        title = title_match.group(1).strip() if title_match else b[:80].strip()
        title_norm = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        if not title_norm or title_norm in seen:
            continue
        seen.add(title_norm)

        candidates.append((score_block(b), b))

    if not candidates:
        # Search ran, but our heuristics filtered everything out.
        # Caller can use this to show a "try a narrower topic" message.
        return ""

    candidates.sort(key=lambda x: x[0], reverse=True)
    ranked_blocks = [b for _, b in candidates[:5]]

    def parse_block(block: str) -> tuple[str, str, str]:
        title_match = re.search(r"(?m)^\[\d+\]\s*(.+)$", block)
        title = (title_match.group(1).strip() if title_match else "(No title)")
        src_match = re.search(r"(?im)^Source:\s*(\S+)\s*$", block)
        source_url = src_match.group(1).strip() if src_match else ""
        body_lines: list[str] = []
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            if re.match(r"^\[\d+\]\s*", line):
                continue
            if re.match(r"(?i)^Source:\s*", line):
                continue
            body_lines.append(line)
        body = " ".join(body_lines).strip()
        return title, body, source_url

    parsed = [parse_block(b) for b in ranked_blocks]

    def _strip_recency_prefix(text: str) -> str:
        return re.sub(
            r"^\d+\s+(?:minutes?|hours?|days?|weeks?|months?)\s+ago\s*[-–·]\s*",
            "",
            text,
            flags=re.I,
        ).strip()

    def _ensure_sentence(text: str) -> str:
        t = (text or "").strip()
        if not t:
            return t
        if t[0].isalpha() and t[0].islower():
            t = t[0].upper() + t[1:]
        if t[-1] not in ".!?":
            t += "."
        return t

    parts: list[str] = []
    for idx, (title, body, source_url) in enumerate(parsed, start=1):
        body_clean = _strip_recency_prefix((body or "").strip())
        title_clean = _strip_recency_prefix((title or "").strip())
        primary = _effective_article_blurb(title_clean, body_clean or title_clean)
        if not primary:
            primary = title_clean or body_clean
        snippet = _blurb_preview(primary, max_len=None)
        if not snippet:
            snippet = _blurb_preview(title_clean, max_len=None)
        snippet = _ensure_sentence(snippet)
        if source_url:
            parts.append(f"{snippet} [[{idx}]]({source_url})")
        else:
            parts.append(f"{snippet} [[{idx}]]")

    if not parts:
        return ""
    return "\n\n".join(parts).strip()

