"""Translation service using DeepL API for Jarvis."""
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"


async def translate_text(
    text: str,
    target_lang: str,
    api_key: str,
    source_lang: str | None = None,
    formality: str | None = None,
) -> dict[str, Any]:
    """
    Translate text using DeepL.

    Returns {"translated_text": "..."} on success or {"error": "..."} on failure.
    target_lang should be a DeepL language code like EN, DE, FR, ES, JA, ZH, etc.
    """
    if not (api_key and api_key.strip()):
        return {"error": "Translation is not configured (missing DEEPL_API_KEY)."}
    text = (text or "").strip()
    if not text:
        return {"error": "No text provided to translate."}

    params: dict[str, str] = {
        "auth_key": api_key,
        "text": text,
        "target_lang": target_lang.upper(),
    }
    if source_lang:
        params["source_lang"] = source_lang.upper()
    if formality:
        # DeepL supports "default", "more", "less" for some languages
        params["formality"] = formality

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession() as session:
            async with session.post(DEEPL_API_URL, data=params, timeout=timeout) as r:
                data = await r.json()
        if "message" in data and "error" in data.get("message", "").lower():
            return {"error": data.get("message", "Unknown DeepL error")}
        translations = data.get("translations") or []
        if not translations:
            return {"error": "No translation returned from DeepL."}
        return {
            "translated_text": translations[0].get("text", "").strip(),
            "detected_source_lang": translations[0].get("detected_source_language"),
        }
    except aiohttp.ClientError as e:
        logger.exception("DeepL API request failed")
        return {"error": str(e)}
    except Exception as e:
        logger.exception("Translation failed")
        return {"error": str(e)}


def format_translation_as_text(data: dict[str, Any]) -> str:
    """Format DeepL translation result as plain text for Jarvis."""
    if "error" in data:
        return f"Translation error: {data['error']}"
    src = data.get("detected_source_lang")
    if src:
        return f"(Detected {src}) {data['translated_text']}"
    return data["translated_text"]

