# bot.py

import os
import random
import wikipedia
import discord
import requests
import json
from googletrans import Translator

TOKEN = 'ODAwMTM0MTMwMTYyNzI5MDIw.YANs-g.cbSBiLAtAF02RKm4bMjsVRCiXIw'
GUILD = '694661342145151026'

client = discord.Client()

def jokes(f):
    
    data = requests.get(f)
    tt = json.loads(data.text)
    return tt

@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == GUILD:
            break

    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

    members = '\n - '.join([member.name for member in guild.members])
    print(f'Guild Members:\n - {members}')
    

    #################### W I K I P E D I A ######################

def wiki_define(arg):
    try:
        img = random.choice(wikipedia.WikipediaPage(title=arg).images)
        definition = img+'\n'+wikipedia.summary(arg, sentences=1, chars=100, 
        auto_suggest=False, redirect=True)
    except wikipedia.exceptions.PageError:
        err = wiki_search(arg)
        definition = '**Error: Page not found**\n__Did you mean:__\n'+err
        
    return definition

def wiki_summary(arg):
    try:
        img = random.choice(wikipedia.WikipediaPage(title=arg).images)
        definition = img+'\n'+wikipedia.summary(arg, sentences=5, chars=1000, 
        auto_suggest=False, redirect=True)
    except wikipedia.exceptions.PageError:
        err = wiki_search(arg)
        definition = '**Error: Page not found**\n__Did you mean:__\n'+err
    return definition

def wiki_search(arg):
    print(wikipedia.search(arg, results=10, suggestion=False))
    results = wikipedia.search(arg, results=10, suggestion=False)
    rslt = '\n'.join(results)
    return '`'+rslt+'`'

greet = ['Hi ', 'Hello ', 'What\'s up, ', 'Greetings, ', 'Sup ']


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!define'):
        words = message.content
        print(words[7:])
        important_words = words[7:]
        await message.channel.send(wiki_define(important_words))
        
    if message.content.startswith('!summary'):
        words = message.content
        print(words[8:])
        important_words = words[8:]
        await message.channel.send(wiki_summary(important_words))
        
    if message.content.startswith('!search'):
        words = message.content
        print(words[7:])
        important_words = words[7:]
        await message.channel.send(wiki_search(important_words))

    #################### G R E E T I N G S ######################

    if message.content.startswith('hey jarvis'):
        words = message.content
        mention = message.author.mention
        print(words)
        await message.channel.send(random.choice(greet)+mention)
        
    if message.content.startswith('hi jarvis'):
        words = message.content
        mention = message.author.mention
        print(words)
        await message.channel.send(random.choice(greet)+mention)

    if message.content.startswith('hello jarvis'):
        words = message.content
        mention = message.author.mention
        print(words)
        await message.channel.send(random.choice(greet)+mention)

    if message.content.startswith('sup jarvis'):
        words = message.content
        mention = message.author.mention
        print(words)
        await message.channel.send(random.choice(greet)+mention)

    if message.content.startswith('yo jarvis'):
        words = message.content
        mention = message.author.mention
        print(words)
        await message.channel.send(random.choice(greet)+mention)

    #################### M I S C E L L A N E O U S ######################

    if message.content.startswith('thanks jarvis'):
        words = message.content
        print(words)
        await message.channel.send('You\'re welcome')

    if message.content.startswith('jarvis i love you'):
        words = message.content
        print(words)
        await message.channel.send('I love you, too')
        
    if message.content.startswith('thank you jarvis'):
        words = message.content
        print(words)
        await message.channel.send('You\'re welcome')

    if message.content.startswith('jarvis tell me a joke'):
        words = message.content
        print(words[7:])
        important_words = words[7:]
        f = r"https://official-joke-api.appspot.com/random_joke"
        a = jokes(f)
        await message.channel.send(a["setup"]+'\n'+'||'+a["punchline"]+'||')
        
    if message.content.startswith('!echo'):
        words = message.content
        print(words[5:])
        await message.channel.send(words[5:])

    if message.content.startswith('fuck you jarvis'):
        words = message.content
        mention = message.author.mention
        print(words)
        await message.channel.send('That\'s not very nice.')


client.run(TOKEN)
