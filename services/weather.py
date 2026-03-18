"""Weather API service. Returns structured data for use by Jarvis tools and Discord embeds."""
import logging
from typing import Any

import aiohttp
import discord

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.weatherapi.com/v1/forecast.json"
HISTORY_URL = "https://api.weatherapi.com/v1/history.json"


async def get_weather_data(city: str, api_key: str, date: str | None = None) -> dict[str, Any]:
    """
    Fetch weather for a city.

    - If date is None: current conditions + forecast.
    - If date (YYYY-MM-DD) is provided: historical data for that date.
    Returns structured dict on success, or {"error": "message"} on failure.
    """
    if not (api_key and api_key.strip()):
        return {"error": "Weather API is not configured (missing WEATHER_API_KEY)."}
    city = (city or "").strip()
    if not city:
        return {"error": "City name is required."}
    try:
        date = (date or "").strip() or None
        if date:
            url = f"{HISTORY_URL}?key={api_key}&q={city}&dt={date}&aqi=no"
        else:
            url = f"{FORECAST_URL}?key={api_key}&q={city}&aqi=no"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
        if "error" in data:
            return {"error": data["error"].get("message", "Unknown error")}
        # History and forecast responses both have forecast.forecastday[0]
        payload: dict[str, Any] = {
            "location": data["location"],
            "forecast": data["forecast"],
            "is_historical": bool(date),
        }
        if date:
            # For history, use the day's aggregated data as "current-like"
            day = data["forecast"]["forecastday"][0]["day"]
            cond = day["condition"]
            # Map into a current-like structure so embed/text formatters can reuse.
            cur = {
                "temp_f": day["avgtemp_f"],
                "feelslike_f": day["avgtemp_f"],
                "humidity": day["avghumidity"],
                "wind_mph": day.get("maxwind_mph", 0),
                "wind_dir": "",  # not present in daily aggregates
                "pressure_in": 0,
                "uv": day.get("uv", 0),
                "last_updated": data["location"]["localtime"],
            }
            payload["current"] = cur
            payload["condition"] = cond
            payload["date"] = date
        else:
            payload["current"] = data["current"]
            payload["condition"] = data["current"]["condition"]
        return payload
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
    base = (
        f"{loc['name']}, {loc['region']}, {loc['country']}: {cur['temp_f']}°F (feels like {cur['feelslike_f']}°F), "
        f"{cond['text']}. High {day['maxtemp_f']}°F, Low {day['mintemp_f']}°F. "
        f"Humidity {cur['humidity']}%, wind {cur['wind_mph']} mph {cur['wind_dir']}. "
        f"Chance of rain {day['daily_chance_of_rain']}%."
    )
    if data.get("is_historical") and data.get("date"):
        return f"Historical weather for {data['date']}: " + base
    return base


def build_weather_embed(data: dict[str, Any]) -> discord.Embed:
    """Build Discord embed from weather service dict."""
    if "error" in data:
        return discord.Embed(title="Error", description=data["error"], color=0xE74C3C)

    loc = data["location"]
    cur = data["current"]
    cond = data["condition"]
    forecast = data["forecast"]["forecastday"][0]
    day = forecast["day"]
    astro = forecast["astro"]

    title = f"{loc['name']}, {loc['region']}, {loc['country']}"
    if data.get("is_historical") and data.get("date"):
        title = f"{title} — {data['date']}"
    embed = discord.Embed(title=title)
    embed.add_field(name="Temperature", value=f"{cur['temp_f']}°F", inline=False)
    embed.add_field(name="Humidity", value=f"{cur['humidity']}%", inline=False)
    embed.add_field(name="Feels Like", value=f"{cur['feelslike_f']}°F", inline=False)
    embed.add_field(name="High", value=f"{day['maxtemp_f']}°F", inline=True)
    embed.add_field(name="Low", value=f"{day['mintemp_f']}°F", inline=True)
    embed.add_field(name="Chance of Rain", value=f"{day['daily_chance_of_rain']}%", inline=True)
    embed.add_field(name="Wind Speed", value=f"{cur['wind_mph']} mph", inline=True)
    embed.add_field(name="Wind Direction", value=cur["wind_dir"], inline=True)
    embed.add_field(name="Pressure", value=f"{cur['pressure_in']} in", inline=True)
    embed.add_field(name="UV Index", value=str(cur["uv"]), inline=True)
    embed.add_field(name="Sunrise", value=astro["sunrise"], inline=True)
    embed.add_field(name="Sunset", value=astro["sunset"], inline=True)
    embed.set_footer(text=f"Last updated at {cur['last_updated']}")
    embed.set_thumbnail(url="https:" + cond["icon"])
    return embed
