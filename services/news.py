"""News API service. Returns structured data for use by Jarvis tools and Discord embeds."""
from __future__ import annotations

import html
import logging
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import aiohttp
import discord

import config

if TYPE_CHECKING:
    from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_aiohttp_session: aiohttp.ClientSession | None = None


async def _get_aiohttp_session() -> aiohttp.ClientSession:
    global _aiohttp_session
    if _aiohttp_session is None or _aiohttp_session.closed:
        _aiohttp_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={"User-Agent": "JarvisBot/1.0 (+news)"},
        )
    return _aiohttp_session


async def close_news_http_session() -> None:
    """Close the shared NewsAPI session (call on bot shutdown to avoid asyncio warnings)."""
    global _aiohttp_session
    if _aiohttp_session is not None and not _aiohttp_session.closed:
        await _aiohttp_session.close()
    _aiohttp_session = None


def news_error_message(data: dict[str, Any]) -> str:
    """Human-readable message for NewsAPI failures (supports typed or legacy string errors)."""
    e = data.get("error")
    if isinstance(e, dict):
        return str(e.get("message") or "")
    if isinstance(e, str):
        return e
    return ""


def news_error_type(data: dict[str, Any]) -> str:
    e = data.get("error")
    if isinstance(e, dict):
        return str(e.get("type") or "error")
    if "error" in data:
        return "error"
    return ""


def _news_err(err_type: str, message: str) -> dict[str, Any]:
    return {"error": {"type": err_type, "message": message}}


def _looks_like_date_only(text: str) -> bool:
    """True when description is basically a calendar line (common bad NewsAPI snippet)."""
    s = re.sub(r"\s+", " ", (text or "").strip())
    if len(s) > 160:
        return False
    if not re.search(
        r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
        s,
        re.I,
    ):
        return False
    if not re.search(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December|"
        r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b",
        s,
        re.I,
    ):
        return False
    if not re.search(r"\b20\d{2}\b", s):
        return False
    return len(re.findall(r"[A-Za-z]+", s)) <= 16


def _is_boilerplate(text: str) -> bool:
    """SEO / subscription filler that should never be summarized as substance."""
    s = (text or "").strip().lower()
    if not s:
        return True
    if re.search(
        r"(stay (up to date|updated)|latest developments|follow .{0,48} news|"
        r"sign up|subscribe|for all the latest|read more at|\bget the latest\b)",
        s,
    ):
        return True
    return False


def _looks_like_multi_headline_dump(text: str) -> bool:
    """Aggregator / snippet packing several unrelated headlines or timestamps."""
    if not text:
        return False
    if len(text) < 100:
        return False
    t = text.lower()
    if len(re.findall(r"\d{1,2}\s+(hours?|days?|minutes?)\s+ago", t)) >= 2:
        return True
    if "·" in text and text.count("·") >= 2:
        return True
    ago_hits = t.count(" ago")
    mid_dots = t.count("ago ·") + t.count("ago -")
    if (ago_hits + mid_dots >= 2) or (ago_hits >= 2 and len(text) > 220):
        return True
    caps = re.findall(r"[A-Z][^.!?\n]{25,}", text)
    if len(caps) >= 3:
        return True
    if text.count(" | ") >= 2 or t.count(", and ") >= 2:
        return True
    return False


_NEWS_QUERY_STOPWORDS = frozenset(
    "a an the and or but in on at to for of as is are was were be been being "
    "it its this that these those i you we they he she what which who whom "
    "when where why how all any both each few more most other some such than "
    "too very can could should would may might must shall will do did does doing "
    "done get got give gave me my our your their news headlines headline latest "
    "show tell ask give current events happening today todays breaking please "
    "just only also not no yes about from into with without".split()
)


def _query_tokens(query: str) -> list[str]:
    raw = (query or "").lower()
    return [
        t
        for t in re.findall(r"[a-z0-9]+", raw, flags=re.I)
        if len(t) > 2 and t not in _NEWS_QUERY_STOPWORDS
    ]


def _article_matches_query(article: dict[str, Any], query: str) -> bool:
    """Drop obvious cross-topic junk when the user asked for a specific topic."""
    tokens = _query_tokens(query)
    if not tokens:
        return True
    text = f"{article.get('title', '')} {article.get('description', '')}".lower()
    matches = sum(1 for tok in tokens if tok in text)
    if len(tokens) == 1:
        return matches >= 1
    return matches >= 2


def _is_valid_article(title: str, description: str) -> bool:
    """Hard drop invalid rows before ranking or synthesis."""
    title = (title or "").strip()
    description = (description or "").strip()
    combined = f"{title} {description}".strip()
    if not combined:
        return False
    if _is_boilerplate(combined):
        return False
    if _looks_like_multi_headline_dump(description):
        return False
    if _looks_like_date_only(description) and _is_boilerplate(title.lower()):
        return False
    words = re.findall(r"\w+", combined)
    if len(words) < 12:
        return False
    return True


def _effective_article_blurb(title: str, description: str) -> str:
    """Pick substantive text; fall back to headline when description is junk."""
    title = (title or "").strip()
    description = (description or "").strip()
    if not title and not description:
        return ""
    if not description:
        return title
    if (
        _looks_like_date_only(description)
        or _is_boilerplate(description)
        or _looks_like_multi_headline_dump(description)
    ):
        return title
    return description


def _dedupe_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for a in articles:
        title = (a.get("title") or "")[:80].lower().strip()
        key = title or ((a.get("url") or "")[:120]).lower().strip()
        if not key:
            key = str(id(a))
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def _score_article(title: str, description: str) -> float:
    """Higher = better candidate to keep in the top-N shown to the model."""
    score = 0.0
    text = f"{title} {description}".lower()

    if _looks_like_date_only(description):
        score -= 2.0
    if _looks_like_multi_headline_dump(description):
        score -= 2.0
    if _is_boilerplate(description):
        score -= 1.5

    word_count = len(re.findall(r"\w+", text))
    score += min(word_count / 50.0, 2.0)

    if re.search(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", title or ""):
        score += 0.5

    return score


def _article_xml_block(article_id: int, src: str, title: str, url: str, content: str) -> str:
    return (
        f'<article id="{article_id}">\n'
        f"<source>{html.escape(src, quote=False)}</source>\n"
        f"<title>{html.escape(title, quote=False)}</title>\n"
        f"<url>{html.escape(url, quote=False)}</url>\n"
        f"<content>{html.escape(content, quote=False)}</content>\n"
        "</article>"
    )


def _citation_map_lines(articles: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for i, a in enumerate(articles, start=1):
        u = (a.get("url") or "").strip()
        lines.append(f"[{i}] -> {u}")
    return "\n".join(lines)


def _truncate_clean(text: str, max_len: int) -> str:
    """Truncate at sentence or word boundary without trailing ellipsis."""
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    last = cut.rfind(". ")
    if last > max_len // 3:
        return cut[: last + 1].strip()
    sp = cut.rfind(" ")
    if sp > max_len // 4:
        return cut[:sp].strip()
    return cut.strip()


def _valid_news_summary(text: str) -> bool:
    """Lightweight check that inline Discord citations are present."""
    return "[[" in text and "]](" in text


def is_news_summary_valid(text: str) -> bool:
    """Public guard: synthesized user-facing news must include citation links."""
    return _valid_news_summary((text or "").strip())


async def get_news_data(query: str | None, api_key: str) -> dict[str, Any]:
    """
    Fetch headline news. Optional topic; empty query = top US headlines.
    Returns {"articles": [...]} on success, or {"error": {"type", "message"}} on failure.
    """
    if not (api_key and api_key.strip()):
        return _news_err(
            "invalid_key",
            "News API is not configured (missing NEWS_API_KEY).",
        )

    page_size = max(5, min(100, config.JARVIS_NEWS_FETCH_PAGE_SIZE))
    q_param = (query or "").strip()

    try:
        if q_param:
            url = (
                "https://newsapi.org/v2/top-headlines?"
                f"language=en&q={quote(q_param)}&pageSize={page_size}&apiKey={api_key}"
            )
        else:
            url = (
                "https://newsapi.org/v2/top-headlines?"
                f"country=us&pageSize={page_size}&apiKey={api_key}"
            )

        session = await _get_aiohttp_session()
        async with session.get(url) as r:
            if r.status == 401:
                return _news_err(
                    "invalid_key",
                    "News API rejected the key (HTTP 401). Check NEWS_API_KEY.",
                )
            try:
                data = await r.json(content_type=None)
            except Exception as exc:
                logger.exception("News API: invalid JSON")
                return _news_err(
                    "api_error",
                    f"Unexpected response from News API (HTTP {r.status}): {exc}",
                )

        if not isinstance(data, dict):
            return _news_err("api_error", "Invalid response from News API.")

        if data.get("status") == "error":
            msg = str(data.get("message") or "Unknown News API error")
            code = str(data.get("code") or "").lower()
            if "apikey" in code or "key" in code:
                return _news_err("invalid_key", msg)
            return _news_err("api_error", msg)

        raw_articles = list(data.get("articles") or [])
        if not raw_articles:
            return _news_err(
                "no_results",
                "No news articles found for that topic.",
            )

        # Strict pipeline: valid rows → relevance → dedupe → rank → top 5
        filtered = [
            a
            for a in raw_articles
            if _is_valid_article(
                (a.get("title") or "").strip(),
                (a.get("description") or "").strip(),
            )
        ]
        if q_param:
            rel = [a for a in filtered if _article_matches_query(a, q_param)]
            if rel:
                filtered = rel
        if not filtered:
            return _news_err(
                "no_results",
                "No usable news articles matched that topic after filtering. Try a more specific query.",
            )

        picked = _dedupe_articles(filtered)
        picked.sort(
            key=lambda a: _score_article(
                (a.get("title") or "").strip(),
                (a.get("description") or "").strip(),
            ),
            reverse=True,
        )
        top = picked[:5]

        out = []
        for a in top:
            out.append({
                "title": (a.get("title") or "").strip() or "(No title)",
                "description": (a.get("description") or "").strip() or "",
                "url": (a.get("url") or "").strip() or "",
                "source": (a.get("source") or {}).get("name", "Unknown"),
                "image_url": (a.get("urlToImage") or "").strip() or "",
            })
        return {"articles": out}
    except aiohttp.ClientError as e:
        logger.exception("News API request failed")
        return _news_err("network_error", str(e))
    except Exception as e:
        logger.exception("News lookup failed")
        return _news_err("unknown_error", str(e))


def _blurb_preview(text: str, *, max_len: int | None = None) -> str:
    """Strip tags, collapse whitespace; optional soft cap at sentence/word boundary (no '...')."""
    s = (text or "").strip()
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s*\.\.\.\s*", " ", s)
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r",(?=[A-Z])", ", ", s)
    s = re.sub(r"(?<=[.!?])(?=[A-Z])", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if max_len is not None and len(s) > max_len:
        cut = s[:max_len]
        best = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
        if best >= max_len // 4:
            s = cut[: best + 1].strip()
        elif (last_sp := cut.rfind(" ")) > max_len // 4:
            s = cut[:last_sp].strip()
        else:
            s = cut.strip()
    return s


def format_news_tool_digest(data: dict[str, Any]) -> str:
    """Structured article bundle for the model (not a user-facing summary)."""

    if "error" in data:
        msg = news_error_message(data)
        et = news_error_type(data)
        return f"News API error ({et}): {msg}"
    articles = data.get("articles") or []
    if not articles:
        return "No news articles found."

    lines: list[str] = [
        f"NewsAPI: {len(articles)} articles retrieved (ranked/deduped). Read ALL blocks below.",
        "The user-facing reply will be a separate synthesized summary; keep your tool follow-up reasoning concise.",
        "",
        "CITATION MAP (for reference; same indices as user summary):",
        _citation_map_lines(articles),
        "",
    ]
    blocks: list[str] = []
    for i, article in enumerate(articles, start=1):
        title = (article.get("title") or "").strip() or "(No title)"
        desc = (article.get("description") or "").strip()
        src = (article.get("source") or "").strip() or "Unknown"
        url = (article.get("url") or "").strip()
        primary = _effective_article_blurb(title, desc)
        body = _blurb_preview(primary, max_len=2500)
        blocks.append(_article_xml_block(i, src, title, url, body))
    lines.extend(blocks)
    return "\n".join(lines).strip()


async def synthesize_news_bundle(
    client: AsyncOpenAI,
    *,
    articles: list[dict[str, Any]],
    user_query: str,
) -> str:
    """One cohesive summary from all articles, with inline [[n]](url) citations."""

    if not articles:
        return ""

    blocks: list[str] = []
    for i, a in enumerate(articles, start=1):
        title = (a.get("title") or "").strip()
        desc = (a.get("description") or "").strip()
        src = (a.get("source") or "").strip() or "Unknown"
        url = (a.get("url") or "").strip()
        primary = _effective_article_blurb(title, desc)
        body = _blurb_preview(primary, max_len=2500)
        blocks.append(_article_xml_block(i, src, title or "(No title)", url, body))
    articles_body = "\n\n".join(blocks)
    citation_map = _citation_map_lines(articles)

    instruction = (
        "You are generating a news summary for display in Discord.\n\n"
        "TASK:\n"
        "Read all provided article blocks and produce ONE cohesive summary that directly answers the user's question.\n\n"
        "OUTPUT FORMAT (strict):\n"
        "- 1 to 3 short paragraphs\n"
        "- Each paragraph: 2 to 5 complete sentences\n"
        "- No bullet points, no lists, no fragments\n"
        "- No ellipses (...), no timestamps, no boilerplate phrases\n\n"
        "CITATIONS (strict):\n"
        "- Every factual claim must be immediately followed by a citation\n"
        "- Use this exact format: [[index]](url)\n"
        "- Example: [[1]](https://example.com/article)\n"
        "- Only use URLs from the CITATION MAP below; each [n] maps to exactly one URL\n"
        "- Never reuse the same URL under a different index\n"
        "- Do NOT use bare numbers\n"
        "- Do NOT add a 'Sources' section\n"
        "- Do NOT invent or modify URLs\n"
        "- Do NOT enumerate articles as [1/5] or paste raw titles/descriptions; write a real summary\n\n"
        "CONTENT RULES:\n"
        "- Synthesize across articles; do NOT summarize each article separately\n"
        "- Prioritize the most relevant and recent information\n"
        "- Ignore empty, boilerplate, or non-informative blurbs\n"
        "- If an article lacks content, rely on its title only if meaningful\n\n"
        "EDGE CASES:\n"
        "- If articles conflict, present the disagreement clearly\n"
        "- If information is insufficient, produce the best possible partial answer without fabrication\n\n"
        "INTERNAL STEPS (do not output):\n"
        "1. Extract key facts from each article\n"
        "2. Merge overlapping facts\n"
        "3. Identify 2–4 main themes\n"
        "4. Write a unified narrative\n\n"
        "INTERNAL STRATEGY (do not output):\n"
        "- Identify 2–4 key themes\n"
        "- Merge overlapping facts\n"
        "- Order by importance to the user query\n\n"
        f"USER QUESTION:\n{user_query.strip()[:500]}\n\n"
        "CITATION MAP:\n"
        f"{citation_map}\n\n"
        "ARTICLES:\n"
        f"{articles_body}"
    )
    temp = float(config.JARVIS_NEWS_SUMMARY_TEMPERATURE)
    last_out = ""
    try:
        for _ in range(2):
            r = await client.chat.completions.create(
                model=config.JARVIS_NEWS_SUMMARY_MODEL,
                messages=[{"role": "user", "content": instruction}],
                temperature=temp,
                max_tokens=config.JARVIS_NEWS_SUMMARY_MAX_TOKENS,
            )
            last_out = (r.choices[0].message.content or "").strip()
            if _valid_news_summary(last_out):
                return last_out
        return last_out
    except Exception:
        logger.exception("synthesize_news_bundle failed")
        return last_out


def build_news_embeds(data: dict[str, Any]) -> list[discord.Embed]:
    """Build one embed per news article for pagination."""
    if "error" in data:
        msg = news_error_message(data) or "Unknown error."
        et = news_error_type(data)
        return [
            discord.Embed(
                title="News error",
                description=f"**{et}**\n{msg}"[:4096],
                color=0xE74C3C,
            )
        ]
    embeds: list[discord.Embed] = []
    for idx, article in enumerate(data["articles"], start=1):
        title = article["title"]
        desc = article["description"] or "No description available."
        url = article["url"]
        source = article["source"]
        image_url = article.get("image_url") or ""

        embed = discord.Embed(
            title=f"[{idx}] {title}",
            description=_truncate_clean(desc, 400),
            url=url or None,
        )
        if url:
            embed.add_field(name="Link", value=url, inline=False)
        embed.set_footer(text=f"Source: {source}")
        if image_url:
            embed.set_image(url=image_url)
        embeds.append(embed)
    return embeds


class NewsPaginatorView(discord.ui.View):
    """Simple button-based paginator for a list of news embeds."""

    def __init__(self, pages: list[discord.Embed], *, timeout: float | None = 60):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.index = 0

    async def _update(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        self.index = (self.index - 1) % len(self.pages)
        await self._update(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        self.index = (self.index + 1) % len(self.pages)
        await self._update(interaction)
