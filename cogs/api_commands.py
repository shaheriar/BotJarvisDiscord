"""API-backed commands: weather, stocks, crypto. Use shared services and proper argument parsing."""
from datetime import datetime

import discord
from discord.ext import commands

import config
from services import crypto as crypto_svc
from services import stocks as stocks_svc
from services import weather as weather_svc


def _weather_embed(data: dict) -> discord.Embed:
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


def _stocks_embed(data: dict) -> discord.Embed:
    """Build Discord embed from stocks service dict."""
    if "error" in data:
        return discord.Embed(title="Error", description=data["error"], color=0xE74C3C)
    embed = discord.Embed(
        title=f"Today's Stock Market Information for {data['symbol']}",
    )
    embed.add_field(name="Name", value=data["description"], inline=False)
    embed.add_field(name="Current Price", value=f"${data['current']}", inline=False)
    embed.add_field(name="Change", value=f"${data['change']}", inline=True)
    embed.add_field(name="Percent Change", value=f"{data['change_percent']}%", inline=True)
    embed.add_field(name="High", value=f"${data['high']}", inline=True)
    embed.add_field(name="Low", value=f"${data['low']}", inline=True)
    embed.add_field(name="Open", value=f"${data['open']}", inline=True)
    embed.add_field(name="Previous Close Price", value=f"${data['previous_close']}", inline=True)
    embed.set_footer(text=datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
    if data.get("logo"):
        embed.set_thumbnail(url=data["logo"])
    return embed


def _crypto_embed(data: dict) -> discord.Embed:
    """Build Discord embed from crypto service dict."""
    if "error" in data:
        return discord.Embed(title="Error", description=data["error"], color=0xE74C3C)
    if "coins" in data:
        embed = discord.Embed(title="Cryptocurrency Market Today")
        for c in data["coins"]:
            embed.add_field(
                name=f"{c['name']} ({c['symbol']})",
                value=f"${round(c['price_usd'], 5)}",
                inline=True,
            )
        embed.set_footer(text=datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
        return embed
    # Single coin
    name = data["name"]
    symbol = data["symbol"]
    price = data["price_usd"]
    embed = discord.Embed(title=f"Market data for {name} ({symbol})")
    embed.add_field(name="Price", value=f"${round(price, 5)}", inline=False)
    o1 = data.get("ohlcv_1h") or {}
    embed.add_field(name="Last 1 Hour", value="-----------------------------------------------", inline=False)
    embed.add_field(name="Open", value=f"${round(o1.get('open', 0), 5)}", inline=True)
    embed.add_field(name="High", value=f"${round(o1.get('high', 0), 5)}", inline=True)
    embed.add_field(name="Low", value=f"${round(o1.get('low', 0), 5)}", inline=True)
    embed.add_field(name="Close", value=f"${round(o1.get('close', 0), 5)}", inline=True)
    o24 = data.get("ohlcv_24h") or {}
    embed.add_field(name="Last 24 Hours", value="-----------------------------------------------", inline=False)
    embed.add_field(name="Open", value=f"${round(o24.get('open', 0), 5)}", inline=True)
    embed.add_field(name="High", value=f"${round(o24.get('high', 0), 5)}", inline=True)
    embed.add_field(name="Low", value=f"${round(o24.get('low', 0), 5)}", inline=True)
    embed.add_field(name="Close", value=f"${round(o24.get('close', 0), 5)}", inline=True)
    embed.set_footer(text=datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
    return embed


class ApiCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="weather")
    async def weather(self, ctx: commands.Context, *, city: str) -> None:
        if not city or not city.strip():
            await ctx.send("Please provide a city name, e.g. `!weather New York`")
            return
        data = await weather_svc.get_weather_data(city.strip(), config.WEATHER_API_KEY)
        embed = _weather_embed(data)
        await ctx.send(embed=embed)

    @commands.command(name="stocks")
    async def stocks(self, ctx: commands.Context, *, symbol: str) -> None:
        if not symbol or not symbol.strip():
            await ctx.send("Please provide a stock symbol or company name, e.g. `!stocks AAPL`")
            return
        data = await stocks_svc.get_stock_data(symbol.strip(), config.FINNHUB_API_KEY)
        embed = _stocks_embed(data)
        await ctx.send(embed=embed)

    @commands.command(name="crypto")
    async def crypto(self, ctx: commands.Context, symbol: str = "") -> None:
        data = await crypto_svc.get_crypto_data(symbol.strip() if symbol else None)
        embed = _crypto_embed(data)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ApiCommands(bot))
