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
    await bot.load_extension("cogs.general")
    await bot.load_extension("cogs.jarvis")


@bot.event
async def on_ready() -> None:
    await bot.change_presence(activity=discord.Game("@Jarvis"))
    for guild in bot.guilds:
        if config.DISCORD_GUILD is not None and guild.id == config.DISCORD_GUILD:
            break


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author == bot.user:
        return
    if bot.user in message.mentions and not message.content.strip().startswith("!"):
        ctx = await bot.get_context(message)
        jarvis_cmd = bot.get_command("jarvis")
        if jarvis_cmd:
            await ctx.invoke(jarvis_cmd)
        return
    await bot.process_commands(message)


async def main() -> None:
    await load_extensions()
    await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception("Bot crashed")
        print("An error occurred. Restarting the bot in 5 seconds.")
        time.sleep(5)
        raise
