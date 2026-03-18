"""Weather API service. Returns structured data for use by Jarvis tools and Discord embeds."""
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

BASE_URL = "https://api.weatherapi.com/v1/forecast.json"


async def get_weather_data(city: str, api_key: str) -> dict[str, Any]:
    """
    Fetch weather for a city. Returns structured dict on success, or {"error": "message"} on failure.
    """
    if not (api_key and api_key.strip()):
        return {"error": "Weather API is not configured (missing WEATHER_API_KEY)."}
    city = (city or "").strip()
    if not city:
        return {"error": "City name is required."}
    try:
        url = f"{BASE_URL}?key={api_key}&q={city}&aqi=no"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
        if "error" in data:
            return {"error": data["error"].get("message", "Unknown error")}
        return {
            "location": data["location"],
            "current": data["current"],
            "forecast": data["forecast"],
            "condition": data["current"]["condition"],
        }
    except aiohttp.ClientError as e:
        logger.exception("Weather API request failed")
        return {"error": str(e)}
    except Exception as e:
        logger.exception("Weather lookup failed")
        return {"error": str(e)}


def format_weather_as_text(data: dict[str, Any]) -> str:
    """Format weather data as plain text for Jarvis."""
    if "error" in data:
        return f"Weather error: {data['error']}"
    loc = data["location"]
    cur = data["current"]
    cond = data["condition"]
    day = data["forecast"]["forecastday"][0]["day"]
    return (
        f"{loc['name']}, {loc['region']}, {loc['country']}: {cur['temp_f']}°F (feels like {cur['feelslike_f']}°F), "
        f"{cond['text']}. High {day['maxtemp_f']}°F, Low {day['mintemp_f']}°F. "
        f"Humidity {cur['humidity']}%, wind {cur['wind_mph']} mph {cur['wind_dir']}. "
        f"Chance of rain {day['daily_chance_of_rain']}%."
    )
