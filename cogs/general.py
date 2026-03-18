"""General commands: help, invite, dice, coin, 8ball."""
import random

import discord
from discord.ext import commands

import config

HELP_LINES = [
    "**HELP PAGE",
    "__LIST OF COMMANDS__**",
    "**!help** : Opens the help page",
    "**!weather {city}** : Get weather info for any city",
    "**!crypto (optional){symbol}** : Get crypto information in general or about a specific currency",
    "**!stocks {stock}** : Get stock market information about a specific stock",
    "**!coin** : Flip a coin!",
    "**!8ball {text}** : Let the magic 8-Ball decide your fate",
    "**!dice** : Roll a dice and get a random number from 1 to 6",
    "**!invite** : Invite me to other servers!",
    "**!jarvis {question}** or @Jarvis : Ask Jarvis anything (search, define, summarize, weather, stocks, crypto, etc.)",
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
