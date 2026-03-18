"""General commands: help, invite, dice, coin, 8ball."""
import random

import discord
from discord.ext import commands

import config

HELP_LINES = [
    "**HELP PAGE — LIST OF COMMANDS**",
    "",
    "**!help** — Opens this help page",
    "**!weather** <city> — Get weather for any city",
    "**!stocks** <symbol> — Get stock quote (e.g. AAPL)",
    "**!crypto** [symbol] — Top coins, or details for btc, eth, etc.",
    "**!coin** — Flip a coin",
    "**!8ball** [question] — Magic 8-Ball answer",
    "**!dice** — Roll a die (1–6)",
    "**!invite** — Get the bot invite link",
    "**!jarvis** <question> or @Jarvis — Ask Jarvis (search, weather, stocks, crypto, news, etc.)",
]

EIGHTBALL_RESPONSES = [
    "As I see it, yes.",
    "Ask again later.",
    "Better not tell you now.",
    "Cannot predict now.",
    "Concentrate and ask again.",
    "Don't count on it.",
    "It is certain.",
    "It is decidedly so.",
    "Most likely.",
    "My reply is no.",
    "My sources say no.",
    "Outlook not so good.",
    "Outlook good.",
    "Reply hazy, try again.",
    "Signs point to yes.",
    "Very doubtful.",
    "Without a doubt.",
    "Yes.",
    "Yes – definitely.",
    "You may rely on it.",
]


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_cmd(self, ctx: commands.Context) -> None:
        await ctx.send("\n".join(HELP_LINES))

    @commands.command(name="invite")
    async def invite(self, ctx: commands.Context) -> None:
        await ctx.send(f"Invite me to other servers using this link: {config.INVITE_LINK}")

    @commands.command(name="dice")
    async def dice(self, ctx: commands.Context) -> None:
        await ctx.send(str(random.randint(1, 6)))

    @commands.command(name="coin")
    async def coin(self, ctx: commands.Context) -> None:
        await ctx.send(random.choice(["Heads!", "Tails!"]))

    @commands.command(name="8ball")
    async def eightball(self, ctx: commands.Context, *, question: str = "") -> None:
        await ctx.send(random.choice(EIGHTBALL_RESPONSES))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
