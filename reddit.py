import praw
from discord.utils import get
from requests import get
import discord
from discord.ext import commands,tasks
import secretvars
import asyncio

ss = secretvars.secretvars()

reddit = praw.Reddit(client_id=ss.redditid,
                     client_secret=ss.redditsecret,
                     password=ss.redditpassword,
                     user_agent=ss.useragent,
                     username=ss.redditusername)

async def subreddit(ctx, bot):
    words = ctx.message.content
    important_words = words[8:]
    print(important_words)
    try:
        await redditpages(ctx, important_words, bot)
    except discord.errors.HTTPException:
        return

async def redditpages(ctx, important_words, client):
    try:
        contents = reddit.subreddit(important_words).hot(limit=5)
    except Exception as e:
        print(e)
        await ctx.send('Error.')
        return
    
    contents = list(contents)
    pages = 5
    cur_page = 1
    message = await ctx.channel.send(f"__**Page {cur_page}/{pages}**__:\n\n{contents[cur_page-1].title}\n{contents[cur_page-1].url}")
    # getting the message object for editing and reacting

    await message.add_reaction("◀️")
    await message.add_reaction("▶️")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]
        # This makes sure nobody except the command sender can interact with the "menu"

    while True:
        try:
            reaction, user = await client.wait_for("reaction_add", timeout=60, check=check)
            # waiting for a reaction to be added - times out after x seconds, 60 in this
            # example

            if str(reaction.emoji) == "▶️" and cur_page != pages:
                cur_page += 1
                await message.edit(content=f"__**Page {cur_page}/{pages}**__:\n\n{contents[cur_page-1].title}\n{contents[cur_page-1].url}")
                await message.remove_reaction(reaction, user)

            elif str(reaction.emoji) == "◀️" and cur_page > 1:
                cur_page -= 1
                await message.edit(content=f"__**Page {cur_page}/{pages}**__:\n\n{contents[cur_page-1].title}\n{contents[cur_page-1].url}")
                await message.remove_reaction(reaction, user)

            else:
                await message.remove_reaction(reaction, user)
                # removes reactions if the user tries to go forward on the last page or
                # backwards on the first page
        except asyncio.TimeoutError:
            await message.delete()
            break
            # ending the loop if user doesn't react after x seconds
