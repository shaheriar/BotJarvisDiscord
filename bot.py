"""Discord bot entry point. Loads config, creates bot, loads cogs, runs."""
import asyncio
import logging
import time

import discord
from discord.ext import commands

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

intents = discord.Intents().all()
bot = commands.Bot(command_prefix="!", intents=intents)


async def load_extensions() -> None:
    await bot.load_extension("cogs.jarvis")


@bot.event
async def on_ready() -> None:
    await bot.change_presence(activity=discord.Game("@Jarvis"))


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author == bot.user:
        return

    # Mention-only command routing.
    if bot.user in message.mentions:
        ctx = await bot.get_context(message)
        jarvis_cmd = bot.get_command("_jarvis_internal")
        if jarvis_cmd:
            await ctx.invoke(jarvis_cmd)
        return


async def main() -> None:
    await load_extensions()
    try:
        await bot.start(config.DISCORD_TOKEN)
    finally:
        from services import news as news_svc

        await news_svc.close_news_http_session()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception("Bot crashed")
        print("An error occurred. Restarting the bot in 5 seconds.")
        time.sleep(5)
        raise
