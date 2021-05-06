import os
from youtube_dl import YoutubeDL
import random
from Parse import parseForTrans
from langs import pages
from reddit import subreddit
from discord.utils import get
from requests import get
import discord
from discord.ext import commands,tasks
import praw
import requests
import json
import time
from helpfunc import hlp
from wiki import wiki_define,wiki_summary,wiki_search
from weather import wthr
from news import newsfunc
import secretvars
from translate import translator

ss = secretvars.secretvars()
TOKEN = ss.tokenid
GUILD = ss.guild
intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!',intents=intents)
bot.remove_command('help')

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

@bot.command(name='song')
async def play(ctx, *, query):
    
    FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

    video, source = search(query)
    server = ctx.message.guild
    voice = server.voice_client
    title = video['title']
    channel = ctx.author.voice.channel
    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()

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

########################################################
        
@bot.command(name='help')
async def help(ctx):
    await ctx.send(hlp())

@bot.command(name='langs')
async def langs(ctx):
    await pages(ctx, bot)

@bot.command(name='reddit')
async def reddit(ctx):
    await subreddit(ctx, bot)

@bot.command(name='define')
async def defi(ctx):
    words = ctx.message.content
    important_words = words[7:]
    try:
        await message.channel.send(wiki_define(important_words))
    except discord.errors.HTTPException:
        return

@bot.command(name='summary')
async def summ(ctx):
    words = message.content
    important_words = words[8:]
    try:
        await message.channel.send(wiki_summary(important_words))
    except discord.errors.HTTPException:
        return
    
@bot.command(name='search')
async def searc(ctx):
    words = message.content
    important_words = words[7:]
    try:
        await message.channel.send('`'+wiki_search(important_words)+'`')
    except discord.errors.HTTPException:
        return

@bot.command(name='news')
async def new(ctx):
    await newsfunc(ctx, bot)

@bot.command(name='weather')
async def wethr(ctx):
    await wthr(ctx.message)

@bot.command(name='invite')
async def invite(ctx):
    await ctx.send('Invite me to other servers using this link: https://discord.com/api/oauth2/authorize?client_id=800094180041818112&permissions=8&scope=bot')

coin = ['Heads!', 'Tails!']
ball =['As I see it, yes.', 'Ask again later.','Better not tell you now.','Cannot predict now.','Concentrate and ask again.','Don’t count on it.','It is certain.','It is decidedly so.','Most likely.','My reply is no.','My sources say no.','Outlook not so good.','Outlook good.','Reply hazy, try again.','Signs point to yes.','Very doubtful.','Without a doubt.','Yes.','Yes – definitely.','You may rely on it.']

@bot.command(name='dice')
async def dice(ctx):
    await ctx.send(random.randint(1, 6))
    
@bot.command(name='coin')
async def coin(ctx):
    await ctx.send(random.choice(coin))

@bot.command(name='8ball')
async def eightball(ctx):
    await ctx.send(random.choice(ball))

@bot.command(name='echo')
async def echo(ctx):
    await ctx.send(ctx.message.content[5:])

@bot.event
async def on_message(message):
    if message.author == client.user:
        return
        
    #Translate Feature
    if message.content[:3] == '!t ':
        parsedWordArray = parseForTrans(message.content)
        response = translateFeature(parsedWordArray[0], parsedWordArray[1], parsedWordArray[2])
        try:
            await message.channel.send(response)
            time.sleep(1)
        except discord.errors.HTTPException:
            return

    #################### G R E E T I N G S ######################
        
    greet = ['Hi ', 'Hello ', 'What\'s up, ', 'Greetings, ', 'Sup ']
    
    if message.content.startswith('hey jarvis') or message.content.startswith('hi jarvis') or message.content.startswith('hello jarvis') or message.content.startswith('sup jarvis') or message.content.startswith('yo jarvis'):
           
        words = message.content
        mention = message.author.mention
        await message.channel.send(random.choice(greet)+mention)

    #################### M I S C E L L A N E O U S ######################

    if  message.content.startswith('thanks jarvis') or message.content.startswith('thank you jarvis'):
            
        words = message.content
        await message.channel.send('You\'re welcome')

    if message.content.startswith('jarvis i love you'):
        words = message.content
        await message.channel.send('I love you, too')

    if  message.content.startswith('how are you jarvis') or message.content.startswith('how are you doing jarvis'):
            
        words = message.content
        await message.channel.send('I\'m doing quite well.')

    if  message.content.startswith('jarvis shut up') or message.content.startswith('shut up jarvis'):
            
        words = message.content
        await message.channel.send(':(')

    if message.content.startswith('jarvis tell me a joke'):
        words = message.content
        important_words = words[7:]
        f = r"https://official-joke-api.appspot.com/random_joke"
        a = jokes(f)
        await message.channel.send(a["setup"]+'\n'+'||'+a["punchline"]+'||')
        
    await bot.process_commands(message)

    #################### T R A N S L A T E ######################

def translateFeature(srcLang, destLang, message):
    response = translator(srcLang, destLang, message)
    print('PRINTING RESPONSE')
    print(response[0][0][0])
    return response[0][0][0]

bot.run(TOKEN)
