"""Optional Playwright-backed browser fetch for JS-heavy pages."""
from __future__ import annotations

import logging

import config

logger = logging.getLogger(__name__)


async def browser_visit(url: str) -> dict:
    """Render a page in headless browser and return visible text."""
    if not config.BROWSER_ENABLED:
        return {"error": "Browser tool is disabled."}

    try:
        from playwright.async_api import async_playwright
    except Exception:
        return {"error": "Playwright is not installed."}

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=config.PLAYWRIGHT_HEADLESS)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=config.WEB_FETCH_TIMEOUT * 1000)
            text = await page.locator("body").inner_text()
            title = await page.title()
            final_url = page.url
            await context.close()
            await browser.close()
    except Exception as exc:
        logger.exception("browser_visit_failed")
        return {"error": f"Browser visit failed: {exc}"}

    return {
        "url": final_url,
        "title": title,
        "content": (text or "")[: config.WEB_FETCH_MAX_CHARS],
    }


def format_browser_result(data: dict) -> str:
    if "error" in data:
        return f"[browser_visit error] {data.get('error')}"
    return f"Title: {data.get('title')}\nURL: {data.get('url')}\n\n{(data.get('content') or '').strip()}"
