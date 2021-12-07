import wikipedia
import requests
import json
import asyncio
from newsapi import NewsApiClient
import secretvars

ss = secretvars.secretvars()

base_news_url =  "https://newsapi.org/v2/top-headlines?language=en&q="
newsapi = NewsApiClient(api_key=ss.newskey)

async def newsfunc(ctx, client):
    words = ctx.message.content
    important_words = words[6:]
    typeOfNews = important_words
    try:
        complete_url = base_news_url + typeOfNews + "&apiKey=47c3bf3394664eb48d0a803451f2d19c"
        response = requests.get(complete_url)
    except IndexError:
        complete_url = "https://newsapi.org/v2/top-headlines?country=us&apiKey=f7b4326c68b24aee96970d83bb5102f3"
        response = requests.get(complete_url)
    x = response.json()
    def newFormat(num):
        src = x["articles"][num]["source"]["name"]
        author = x["articles"][num]["author"]
        title = x["articles"][num]["title"]
        des = x["articles"][num]["description"]
        url = x["articles"][num]["url"]
        content = x["articles"][num]["content"]
        return src + ":\n" + title + ":\n" + des + " " + url
    if x["status"] != 'error':
        if x["totalResults"] >= 4:
            contents = [newFormat(0), newFormat(1), newFormat(2), newFormat(3)]
        else:
            await ctx.send("Cannot find article")
            return
        await newspages(ctx, client, contents)
    else:
        await ctx.send('News not found')

async def newspages(ctx, client, contents):
    pages = 4
    cur_page = 1
    message = await ctx.channel.send(f"__**Page {cur_page}/{pages}**__:\n\n{contents[cur_page-1]}")
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
                await message.edit(content=f"__**Page {cur_page}/{pages}**__:\n\n{contents[cur_page-1]}")
                await message.remove_reaction(reaction, user)

            elif str(reaction.emoji) == "◀️" and cur_page > 1:
                cur_page -= 1
                await message.edit(content=f"__**Page {cur_page}/{pages}**__:\n\n{contents[cur_page-1]}")
                await message.remove_reaction(reaction, user)

            else:
                await message.remove_reaction(reaction, user)
                # removes reactions if the user tries to go forward on the last page or
                # backwards on the first page
        except asyncio.TimeoutError:
            await message.delete()
            break
            
            # ending the loop if user doesn't react after x seconds
