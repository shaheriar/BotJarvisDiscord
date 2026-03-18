"""Wikipedia lookup service. Returns structured data for use by Jarvis."""
import logging
from typing import Any

import wikipedia

logger = logging.getLogger(__name__)


def wikipedia_lookup(topic: str) -> dict[str, Any]:
    """
    Fetch a short Wikipedia summary for a topic.
    Returns {"summary": str} on success, or {"error": "message"} on failure.
    """
    topic = (topic or "").strip()
    if not topic:
        return {"error": "Topic is required."}
    try:
        titles = wikipedia.search(topic, results=1)
        if not titles:
            return {"error": f"Wikipedia: no results for '{topic}'."}
        page = wikipedia.page(title=titles[0], auto_suggest=False)
        summary = page.summary.split("\n")[0][:1500]
        return {"summary": summary, "title": page.title}
    except wikipedia.exceptions.DisambiguationError as e:
        return {"error": f"Wikipedia: ambiguous. First option: {e.options[0]}"}
    except wikipedia.exceptions.PageError:
        return {"error": f"Wikipedia: no page found for '{topic}'."}
    except Exception as e:
        logger.exception("Wikipedia lookup failed")
        return {"error": str(e)}


def format_wikipedia_as_text(data: dict[str, Any]) -> str:
    """Format Wikipedia data as plain text for Jarvis."""
    if "error" in data:
        return data["error"]
    return data.get("summary", "")
