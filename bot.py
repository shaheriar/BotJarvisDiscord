from yt_dlp import YoutubeDL
import random
from Parse import parseForTrans
from langs import pages
# from reddit import subreddit
import discord
import socket
from aiohttp import ClientConnectorError
from discord.utils import get
from discord.ext import commands
import requests
import time
from helpfunc import hlp
from wiki import wiki_define,wiki_summary,wiki_search
from weather import wthr
from news import newsfunc
import valorantstats
import secretvars
# from translate import translator
from urllib.parse import quote
from crypto import crypto
from stocks import stocks
from openai import OpenAI

ss = secretvars.secretvars()
TOKEN = ss.tokenid
GUILD = ss.guild
intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!',intents=intents)
bot.remove_command('help')

gptClient = OpenAI(api_key=ss.gptkey)
messages = dict()
ffmpeg_options = {
    'options': '-vn'
}

@bot.event
async def on_ready():
    game = discord.Game("!help")
    await bot.change_presence(activity=game)
    for guild in bot.guilds:
        #print(f'{client.user} is connected to the following guild:\n{guild.name}(id: {guild.id})\n')
        if guild.name == GUILD:
            break

    #members = '\n - '.join([member.name for member in guild.members])
    #print(f'Guild Members:\n - {members}')

##################### M U S I C #######################

@bot.command(name='leave')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        await voice_client.connect()
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")

########

def search(query):
    with YoutubeDL({'format': 'bestaudio', 'noplaylist':'True'}) as ydl:
        try: requests.get(query)
        except: info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
        else: info = ydl.extract_info(query, download=False)
    return (info, info['url'])

########

@bot.command(name='jarvis')
async def gpt(ctx):
    query = ctx.message.content.split('!jarvis ')[1]
    sender = str(ctx.message.author.id)
    server = str(ctx.message.guild)
    async with ctx.typing():
        message={
            "role": "user",
            "content": query
        }
        if server not in messages:
            messages[server] = dict()
        if sender not in messages[server]:
            messages[server][sender] = [message]
        else:
            if len(messages[server][sender]) > 100:
                messages[server][sender] = messages[server][sender][50:] # Pruning the list
            messages[server][sender].append(message)
        response = gptClient.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages[server][sender]
        )
        response = response.choices[0].message.content
        messages[server][sender].append({
            "role": "assistant",
            "content": response
        })
    await ctx.send(response)

########

@bot.command(name='song')
async def play(ctx, *, query):
    await ctx.send('Searching for \"' + query + "\"...")
    video, source = search(query)
    server = ctx.message.guild
    voice = server.voice_client
    title = video['title']
    thumbnail = video['thumbnails'][0]
    channel = ctx.author.voice.channel
    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()
    embed = discord.Embed(title='Now playing')
    embed.add_field(name='Song', value=title)
    embed.set_thumbnail(url=thumbnail['url'])
    await ctx.send(embed=embed)

    voice.play(discord.FFmpegPCMAudio(source), after=lambda e: print('done', e))
    # while voice.is_playing():
    #     continue
    # await voice.disconnect()

########

@bot.command(name='pause')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        await voice_client.connect()
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send("Paused.")
    else:
        await ctx.send("The bot is not playing anything at the moment.")

########
    
@bot.command(name='resume')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        await voice_client.connect()
    if voice_client.is_paused():
        voice_client.resume()
        await ctx.send("Resuming.")
    else:
        await ctx.send("The bot was not playing anything before this. Use play_song command")

########

@bot.command(name='stop')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        await voice_client.connect()
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Stopped.")
    else:
        await ctx.send("The bot is not playing anything at the moment.")

########################################################
        
@bot.command(name='help')
async def help(ctx):
    await ctx.send(hlp())

########

@bot.command(name='langs')
async def langs(ctx):
    await pages(ctx, bot)

########

# @bot.command(name='reddit')
# async def reddit(ctx):
#     await subreddit(ctx, bot)

########

@bot.command(name='define')
async def defi(ctx):
    words = ctx.message.content
    important_words = words[7:]
    try:
        embed=wiki_define(important_words)
        await ctx.send(embed=embed)
    except discord.errors.HTTPException as e:
        print("HTTP Exception", e)
        return

########

@bot.command(name='summary')
async def summ(ctx):
    words = ctx.message.content
    important_words = words[8:]
    try:
        embed=wiki_summary(important_words)
        await ctx.send(embed=embed)
    except discord.errors.HTTPException as e:
        print("HTTP Exception", e)
        return

########
    
@bot.command(name='search')
async def searc(ctx):
    words = ctx.message.content
    important_words = words[7:]
    try:
        await ctx.send('`'+wiki_search(important_words)+'`')
    except discord.errors.HTTPException:
        return

########

@bot.command(name='news')
async def new(ctx):
    await newsfunc(ctx, bot)

########

@bot.command(name='weather')
async def wethr(ctx):
    await wthr(ctx)

########

@bot.command(name='invite')
async def invite(ctx):
    await ctx.send('Invite me to other servers using this link: https://discord.com/api/oauth2/authorize?client_id=800094180041818112&permissions=8&scope=bot')

########
            
greet = ['Hi ', 'Hello ', 'What\'s up, ', 'Greetings, ', 'Sup ', 'Howdy ', 'Hey ']

ball = ['As I see it, yes.', 'Ask again later.','Better not tell you now.','Cannot predict now.','Concentrate and ask again.','Don’t count on it.','It is certain.','It is decidedly so.','Most likely.','My reply is no.','My sources say no.','Outlook not so good.','Outlook good.','Reply hazy, try again.','Signs point to yes.','Very doubtful.','Without a doubt.','Yes.','Yes – definitely.','You may rely on it.']

########

@bot.command(name='dice')
async def dice(ctx):
    await ctx.send(random.randint(1, 6))

########
    
@bot.command(name='coin')
async def coin(ctx):
    await ctx.send(random.choice(['Heads!', 'Tails!']))

########

@bot.command(name='8ball')
async def eightball(ctx):
    await ctx.send(random.choice(ball))

########

@bot.command(name='echo')
async def echo(ctx):
    await ctx.send(ctx.message.content[5:])

########

# @bot.command(name='stats')
# async def stat(ctx):
#     await ctx.send(embed=valorantstats.valstats(ctx))

########

@bot.command(name='crypto')
async def cryp(ctx):
    await crypto(ctx)

########

@bot.command(name='stocks')
async def cryp(ctx):
    await stocks(ctx)

########

# @bot.command(name='jarvis')
# async def talk(ctx):
#     query = ctx.message.content.split('!jarvis ')[1]
#     url = "https://jarvisrosehack.herokuapp.com/chatter/" + quote(query)
#     response = requests.request("GET", url)
#     print(response.text)
#     await ctx.send(response.text)

########

@bot.event
async def on_message(message):
    if message.author == client.user:
        return

########
    
    # if message.content[:3] == '!t ':
    #     parsedWordArray = parseForTrans(message.content)
    #     response = translateFeature(parsedWordArray[0], parsedWordArray[1], parsedWordArray[2])
    #     try:
    #         await message.channel.send(response)
    #         time.sleep(1)
    #     except discord.errors.HTTPException:
    #         return

########
    
    if message.content.startswith('hey jarvis') or message.content.startswith('hi jarvis') or message.content.startswith('hello jarvis') or message.content.startswith('sup jarvis') or message.content.startswith('yo jarvis'):
        words = message.content
        mention = message.author.mention
        await message.channel.send(random.choice(greet)+mention)

########

    if  message.content.startswith('thanks jarvis') or message.content.startswith('thank you jarvis'):
        words = message.content
        await message.channel.send('You\'re welcome')
        
########

    if message.content.startswith('jarvis i love you'):
        words = message.content
        await message.channel.send('I love you, too')

########

    if  message.content.startswith('how are you jarvis') or message.content.startswith('how are you doing jarvis'):
        words = message.content
        await message.channel.send('I\'m doing quite well.')
        
########

    if  message.content.startswith('jarvis shut up') or message.content.startswith('shut up jarvis'):
        words = message.content
        await message.channel.send(':(')

########

    if message.content.startswith('jarvis tell me a joke'):
        a = requests.get("https://joke.deno.dev/").json()
        await message.channel.send(a["setup"]+'\n'+'||'+a["punchline"]+'||')

########
        
    await bot.process_commands(message)

########

# def translateFeature(srcLang, destLang, message):
#     response = translator(srcLang, destLang, message)
#     print('PRINTING RESPONSE')
#     print(response[0][0][0])
#     return response[0][0][0]
try:
    bot.run(TOKEN)
except Exception as e:
    print("An error occured. Restarting the bot in 5 seconds.")
    time.sleep(5)
    print(e)
    exit()