# bot.py
import os
import random
import Parse
import discord
from googletrans import Translator
#from dotenv import load_dotenv

#load_dotenv()
translator = Translator(service_urls=['translate.googleapis.com'])
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

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    brooklyn_99_quotes = [
        'I\'m the human form of the 💯 emoji.',
        'Bingpot!','Cool. Cool cool cool cool cool cool cool, no doubt no doubt no doubt no doubt.',
    ]

    if message.content == '99!':
        response = random.choice(brooklyn_99_quotes)
        await message.channel.send(response)
    if message.content == '!jason':
        response = 'jason is on sale for 5 cow no bargain'
        await message.channel.send(response)
    if message.content == '!srk':
        response = 'https://64.media.tumblr.com/eeae49c61424abe31b8639b972079850/tumblr_ntpz7mkHM91uejcvjo4_250.gifv'
        await message.channel.send(response)
    if message.content == '!buy':
        response = 'SOLD! to ' + message.author.name
        await message.channel.send(response)
    if message.content == '!coin':
        response = random.choice(coin)
        await message.channel.send(response)
    
    #Translate Feature
    if message.content[:3] == '!t ':
        parsedWordArray = parseForTrans(message.content)
        response = translateFeature(parsedWordArray[0], parsedWordArray[1], parsedWordArray[2])
        await message.channel.send(response)

def parseForTrans(input):
    parsedWordArray = input[3:].split(' ', 2)
    return parsedWordArray

def translateFeature(srcLang, destLang, message):
    response = translator.translate(message, dest=destLang, src=srcLang)
    return response.text


client.run(TOKEN)
