"""News API service. Returns structured data for use by Jarvis tools and Discord embeds."""
import logging
from typing import Any
from urllib.parse import quote

import aiohttp
import discord

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
        raw_articles = data.get("articles") or []
        if not raw_articles:
            return {"error": "No news articles found for that topic."}
        out = []
        for a in raw_articles[:5]:
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
        return {"error": str(e)}
    except Exception as e:
        logger.exception("News lookup failed")
        return {"error": str(e)}


def format_news_as_text(data: dict[str, Any], *, include_urls: bool = True) -> str:
    """Format news data as plain text for Jarvis.

    When include_urls is False, article URLs are omitted to avoid extra embeds.
    """
    if "error" in data:
        return f"News API error: {data['error']}"
    lines = []
    for i, a in enumerate(data["articles"], 1):
        block = f"[{i}] {a['title']} — {a['source']}"
        if a["description"]:
            block += f"\n{a['description'][:300]}{'...' if len(a['description']) > 300 else ''}"
        if include_urls and a["url"]:
            block += f"\n{a['url']}"
        lines.append(block)
    return "\n\n".join(lines)


def build_news_embeds(data: dict[str, Any]) -> list[discord.Embed]:
    """Build one embed per news article for pagination."""
    if "error" in data:
        return [discord.Embed(title="Error", description=data["error"], color=0xE74C3C)]
    embeds: list[discord.Embed] = []
    for idx, article in enumerate(data["articles"], start=1):
        title = article["title"]
        desc = article["description"] or "No description available."
        url = article["url"]
        source = article["source"]
        image_url = article.get("image_url") or ""

        embed = discord.Embed(
            title=f"[{idx}] {title}",
            description=(desc[:400] + "..." if len(desc) > 400 else desc),
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
