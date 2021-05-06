# bot.py

import os
from youtube_dl import YoutubeDL
import random
from Parse import parseForTrans
from discord.utils import get
from requests import get
import discord
from discord.ext import commands,tasks
import praw
import requests
import json
import time
import wikipedia
import asyncio
import secretvars
from newsapi import NewsApiClient
from translate import translator
#from dotenv import load_dotenv

#load_dotenv()
ss = secretvars.secretvars()
#translator = translator(service_urls=['translate.googleapis.com'])
TOKEN = ss.tokenid
GUILD = ss.guild
weatherkey = ss.weatherkey
base_url = "http://api.openweathermap.org/data/2.5/weather?"
base_news_url =  "https://newsapi.org/v2/top-headlines?language=en&q="
newsapi = NewsApiClient(api_key=ss.newskey)


reddit = praw.Reddit(client_id=ss.redditid,
                     client_secret=ss.redditsecret,
                     password=ss.redditpassword,
                     user_agent=ss.useragent,
                     username=ss.redditusername)

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!',intents=intents)
bot.remove_command('help')

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}


def jokes(f):
    
    data = requests.get(f)
    tt = json.loads(data.text)
    return tt

@bot.event
async def on_ready():
    game = discord.Game("!help")
    await bot.change_presence(activity=game)
    for guild in bot.guilds:
        print(f'{client.user} is connected to the following guild:\n{guild.name}(id: {guild.id})\n')
        if guild.name == GUILD:
            break

    members = '\n - '.join([member.name for member in guild.members])
    print(f'Guild Members:\n - {members}')

##################### M U S I C #######################

async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()

@bot.command(name='leave')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")

def search(query):
    with YoutubeDL({'format': 'bestaudio', 'noplaylist':'True'}) as ydl:
        try: requests.get(query)
        except: info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
        else: info = ydl.extract_info(query, download=False)
    return (info, info['formats'][0]['url'])

@bot.command(name='play_song')
async def play(ctx, *, query):
    await join(ctx)
    #Solves a problem I'll explain later
    FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

    video, source = search(query)
    server = ctx.message.guild
    voice = server.voice_client
    title = video['title']

    #await join(ctx)
    await ctx.send(f'Now playing ' + title)

    voice.play(discord.FFmpegPCMAudio(source, **FFMPEG_OPTS), after=lambda e: print('done', e))
    voice.is_playing()


@bot.command(name='pause')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
        await ctx.send("Paused.")
    else:
        await ctx.send("The bot is not playing anything at the moment.")
    
@bot.command(name='resume')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
        await ctx.send("Resuming.")
    else:
        await ctx.send("The bot was not playing anything before this. Use play_song command")

@bot.command(name='stop')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.stop()
        await ctx.send("Stopped.")
    else:
        await ctx.send("The bot is not playing anything at the moment.")

    #################### W I K I P E D I A ######################

def wiki_define(arg):
    try:
        url = r'https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&titles='+wikipedia.search(arg, results=1, suggestion=False)[0]+'&pithumbsize=500&format=json'
        req = requests.get(url)
        getj = json.loads(req.text)
        try:
            img = list(getj["query"]["pages"].values())[0]["thumbnail"]["source"]
        except KeyError:
            img = ' '
        definition = wikipedia.summary(arg, sentences=1, chars=100, 
        auto_suggest=False, redirect=True)+'\n'+img
    except wikipedia.exceptions.PageError:
        err = '`'+wiki_search(arg)+'`'
        definition = '**Error: Page not found**\n__Did you mean:__\n'+err
    except wikipedia.exceptions.DisambiguationError:
        err = '`'+wiki_search(arg)+'`'
        definition = '__Did you mean:__\n'+err
    except wikipedia.exceptions.WikipediaException:
        return
    return definition

def wiki_summary(arg):
    try:
        url = r'https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&titles='+wikipedia.search(arg, results=1, suggestion=False)[0]+'&pithumbsize=500&format=json'
        req = requests.get(url)
        getj = json.loads(req.text)
        try:
            img = list(getj["query"]["pages"].values())[0]["thumbnail"]["source"]
        except KeyError:
            img = ' '
        definition = wikipedia.summary(arg, sentences=5, chars=1000, 
        auto_suggest=False, redirect=True)+'\n'+img
    except wikipedia.exceptions.PageError:
        err = '`'+wiki_search(arg)+'`'
        definition = '**Error: Page not found**\n__Did you mean:__\n'+err
    except wikipedia.exceptions.DisambiguationError:
        err = '`'+wiki_search(arg)+'`'
        definition = '__Did you mean:__\n'+err
    except wikipedia.exceptions.WikipediaException:
        return
    return definition

def wiki_search(arg):
    print(wikipedia.search(arg, results=10, suggestion=False))
    results = wikipedia.search(arg, results=10, suggestion=False)
    rslt = '\n'.join(results)
    return rslt

greet = ['Hi ', 'Hello ', 'What\'s up, ', 'Greetings, ', 'Sup ']


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!dice'):
        await message.channel.send(random.randint(1, 6))
        
    #Display Languages
    if message.content.startswith('!langs'):
        await pages(message)
        
    #Translate Feature
    if message.content[:3] == '!t ':
        parsedWordArray = parseForTrans(message.content)
        response = translateFeature(parsedWordArray[0], parsedWordArray[1], parsedWordArray[2])
        try:
            await message.channel.send(response)
            time.sleep(1)
        except discord.errors.HTTPException:
            return
        
    if message.content.startswith('!define'):
        words = message.content
        important_words = words[7:]
        try:
            await message.channel.send(wiki_define(important_words))
        except discord.errors.HTTPException:
            return
        
    if message.content.startswith('!summary'):
        words = message.content
        important_words = words[8:]
        try:
            await message.channel.send(wiki_summary(important_words))
        except discord.errors.HTTPException:
            return
        
    if message.content.startswith('!search'):
        words = message.content
        important_words = words[7:]
        try:
            await message.channel.send('`'+wiki_search(important_words)+'`')
        except discord.errors.HTTPException:
            return


    ###################### R E D D I T ########################

    if message.content.startswith('!reddit'):
        words = message.content
        important_words = words[8:]
        print(important_words)
        async def redditpages(ctx):
            try:
                contents = reddit.subreddit(important_words).hot(limit=5)
            except prawcore.exceptions:
                await message.channel.send('Error.')
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
        try:
            await redditpages(message)
        except discord.errors.HTTPException:
            return
    

    #################### G R E E T I N G S ######################

    if message.content.startswith('hey jarvis'):
        words = message.content
        mention = message.author.mention
        await message.channel.send(random.choice(greet)+mention)
        
    if message.content.startswith('hi jarvis'):
        words = message.content
        mention = message.author.mention
        await message.channel.send(random.choice(greet)+mention)

    if message.content.startswith('hello jarvis'):
        words = message.content
        mention = message.author.mention
        await message.channel.send(random.choice(greet)+mention)

    if message.content.startswith('sup jarvis'):
        words = message.content
        mention = message.author.mention
        await message.channel.send(random.choice(greet)+mention)

    if message.content.startswith('yo jarvis'):
        words = message.content
        mention = message.author.mention
        await message.channel.send(random.choice(greet)+mention)

    #################### M I S C E L L A N E O U S ######################

    coin = ['Heads!', 'Tails!']
    ball =['As I see it, yes.', 'Ask again later.','Better not tell you now.','Cannot predict now.','Concentrate and ask again.','Don’t count on it.','It is certain.','It is decidedly so.','Most likely.','My reply is no.','My sources say no.','Outlook not so good.','Outlook good.','Reply hazy, try again.','Signs point to yes.','Very doubtful.','Without a doubt.','Yes.','Yes – definitely.','You may rely on it.']
    
    if message.content.startswith('thanks jarvis'):
        words = message.content
        await message.channel.send('You\'re welcome')

    if message.content.startswith('!invite'):
        words = message.content
        await message.channel.send('Invite me to other servers using this link: https://discord.com/api/oauth2/authorize?client_id=800094180041818112&permissions=8&scope=bot')

    if message.content.startswith('!coin'):
        words = message.content
        await message.channel.send(random.choice(coin))

    if message.content.startswith('!8ball'):
        words = message.content
        await message.channel.send(random.choice(ball))

    if message.content.startswith('jarvis i love you'):
        words = message.content
        await message.channel.send('I love you, too')

    if message.content.startswith('how are you jarvis'):
        words = message.content
        await message.channel.send('I\'m doing quite well.')

    if message.content.startswith('how are you doing jarvis'):
        words = message.content
        await message.channel.send('I\'m doing quite well.')

    if message.content.startswith('shut up jarvis'):
        words = message.content
        await message.channel.send(':(')

    if message.content.startswith('jarvis shut up'):
        words = message.content
        await message.channel.send(':(')
        
    if message.content.startswith('thank you jarvis'):
        words = message.content
        await message.channel.send('You\'re welcome')

    if message.content.startswith('jarvis tell me a joke'):
        words = message.content
        important_words = words[7:]
        f = r"https://official-joke-api.appspot.com/random_joke"
        a = jokes(f)
        await message.channel.send(a["setup"]+'\n'+'||'+a["punchline"]+'||')
        
    if message.content.startswith('!echo'):
        words = message.content
        await message.channel.send(words[5:])

    #################### N E W S ######################

    if message.content.startswith('!news'):
        words = message.content
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
                await message.channel.send("Cannot find article")
                return
            async def newspages(ctx):
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
            await newspages(message)
        else:
            await message.channel.send('News not found')

    #################### W E A T H E R ######################

    if message.content.startswith('!weather'):
        words = message.content
        important_words = words[8:]
        city_name = important_words
        complete_url = base_url + "appid=" + weatherkey + "&units=imperial" + "&q=" + city_name
        response = requests.get(complete_url)
        x = response.json()
        if x["cod"] != "404":
            # store the value of "main" 
            # key in variable y 
            y = x["main"] 
          
            # store the value corresponding 
            # to the "temp" key of y 
            current_temperature = y["temp"] 
          
            # store the value corresponding 
            # to the "pressure" key of y 
            current_pressure = y["pressure"] 
          
            # store the value corresponding 
            # to the "humidity" key of y 
            current_humidity = y["humidity"] 
          
            # store the value of "weather" 
            # key in variable z 
            z = x["weather"]
            f = current_temperature
            f = round(f,0)
            #city_name = city_name.capitalize()
          
            # store the value corresponding  
            # to the "description" key at  
            # the 0th index of z 
            weather_description = '**Weather for' + city_name.title() + ':**' + '\n"' + z[0]["main"] + '" with a temperature of ' + str(f) + '°F and humidity ' + str(current_humidity) + '%'
            await message.channel.send(weather_description)
        else:
            await message.channel.send('City not found')

    #################### H E L P ######################

@bot.command(name='help')
async def help(ctx):
    line1 = '**HELP PAGE\n'
    line2 = '__LIST OF COMMANDS__**\n'
    line3 = '**!help** : Opens the help page\n'
    line4 = '**!define {word}** : Get a one sentence definition of anything\n'
    line5 = '**!summary {word}** : Get a more in depth definition of anything\n'
    line6 = '**!search {word}** : Search for keywords\n'
    line7 = '**!weather {city}** : Get weather info for any city\n'
    line8 = '**!t {source} {destination} {text}** : Translate anything from source language to destination language\n'
    line9 = '**!langs** : Get a list of supported languages to translate\n'
    line10 = '**!news {topic}** : Get a list of news you\'re searching for\n'
    line11 = '**!coin** : Flip a coin!\n'
    line12 = '**!8ball {text}** : Let the magic 8-Ball decide your fate\n'
    line13 = '**!dice** : Roll a dice and get a random number from 1 to 6\n'
    line14 = '**!reddit {subreddit}** : Get the top 5 posts in a subreddit\n'
    line15 = '**!invite** : Invite me to other servers!\n'
    line16 = '**!play_song {query}** : Search or paste a url to play a song in your voice channel\n'
    line17 = '**!leave** : Leave your voice channel\n'
    line18 = '**!pause** : Pause the current song\n'
    line19 = '**!stop** : Stop the current song\n'

    helptext = line1+line2+line3+line4+line5+line6+line7+line8+line9+line10+line11+line12+line13+line14+line15+line16+line17+line18+line19
    await ctx.send(helptext)

    #################### T R A N S L A T E ######################

def translateFeature(srcLang, destLang, message):
    response = translator(srcLang, destLang, message)
    print('PRINTING RESPONSE')
    print(response[0][0][0])
    return response[0][0][0]

#scroll menu
async def pages(ctx):
    contents = [" af: afrikaans \n sq: albanian \n am: amharic \n ar: arabic \n hy: armenian \n az: azerbaijani\n eu: basque \n be: belarusian \n bn: bengali \n bs: bosnian \n bg: bulgarian \n ca: catalan \n ceb: cebuano \n ny: chichewa \n zh-cn: chinese (simplified) \n zh-tw: chinese (traditional) \n co: corsican \n hr: croatian \n cs: czech \n da: danish \n nl: dutch\n en: english \n eo: esperanto \n et: estonian \n tl: filipino \n fi: finnish \n fr: french",
                     " fy: frisian \n gl: galician \n ka: georgian \n de: german \n el: greek \n gu: gujarati \n ht: haitian creole \n ha: hausa \n haw: hawaiian \n iw: hebrew \n he: hebrew \n hi: hindi \n hmn: hmong \n hu: hungarian \n is: icelandic \n ig: igbo \n id: indonesian \n ga: irish \n it: italian \n ja: japanese \n jw: javanese \n kn: kannada \n kk: kazakh \n km: khmer \n ko: korean \n ku: kurdish (kurmanji) \n ky: kyrgyz", 
                     " lo: lao \n la: latin \n lv: latvian \n lt: lithuanian \n lb: luxembourgish \n mk: macedonian \n mg: malagasy \n ms: malay \n ml: malayalam \n mt: maltese \n mi: maori \n mr: marathi \n mn: mongolian \n my: myanmar (burmese) \n ne: nepali \n no: norwegian \n or: odia \n ps: pashto \n fa: persian \n pl: polish \n pt: portuguese \n pa: punjabi \n ro: romanian \n ru: russian \n sm: samoan \n gd: scots gaelic \n sr: serbian", 
                     " st: sesotho \n sn: shona \n sd: sindhi \n si: sinhala \n sk: slovak \n sl: slovenian \n so: somali \n es: spanish \n su: sundanese \n sw: swahili \n sv: swedish \n tg: tajik \n ta: tamil \n te: telugu \n th: thai \n tr: turkish \n uk: ukrainian \n ur: urdu \n ug: uyghur \n uz: uzbek \n vi: vietnamese \n cy: welsh \n xh: xhosa \n yi: yiddish \n yo: yoruba \n zu: zulu"]
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



bot.run(TOKEN)
