"""General commands: help, invite, dice, coin, 8ball."""
import random

import discord
from discord.ext import commands

import config

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="invite")
    async def invite(self, ctx: commands.Context) -> None:
        await ctx.send(f"Invite me to other servers using this link: {config.INVITE_LINK}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
