# bot.py
import os
import random
import wikipedia
import discord

from googletrans import Translator
translator = Translator(service_urls=['translate.googleapis.com'])
response = translator.translate('message', dest='hi', src='en')
print(response.text)

TOKEN = 'ODAwMDk0MTgwMDQxODE4MTEy.YANHxQ.cGNOFsXvysbB09Q1fasmsmLUoVo'
GUILD = '694661342145151026'

client = discord.Client()

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
    

def wiki_define(arg):
    try:
        definition = wikipedia.summary(arg, sentences=1, chars=100, 
        auto_suggest=False, redirect=True)
    except wikipedia.exceptions.PageError:
        definition = 'Error: Page not found'
        
    return definition

def wiki_summary(arg):
    try:
        definition = wikipedia.summary(arg, sentences=5, chars=1000, 
        auto_suggest=False, redirect=True)
    except wikipedia.exceptions.PageError:
        definition = 'Error: Page not found'
    return definition

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
        print(words)
        important_words = words[8:]
        await message.channel.send(wiki_summary(important_words))


client.run(TOKEN)
