# bot.py

import os
import random
import Parse
import discord
import requests
import json
import wikipedia
from googletrans import Translator
#from dotenv import load_dotenv

#load_dotenv()
translator = Translator(service_urls=['translate.googleapis.com'])
TOKEN = 'ODAwMDk0MTgwMDQxODE4MTEy.YANHxQ.cGNOFsXvysbB09Q1fasmsmLUoVo'
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
      
    #Display Languages
    if message.content.startswith('!langs'):
        await pages(message)
        
    #Translate Feature
    if message.content[:3] == '!t ':
        parsedWordArray = parseForTrans(message.content)
        response = translateFeature(parsedWordArray[0], parsedWordArray[1], parsedWordArray[2])
        await message.channel.send(response)
        
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

def parseForTrans(input):
    parsedWordArray = input[3:].split(' ', 2)
    return parsedWordArray

def translateFeature(srcLang, destLang, message):
    response = translator.translate(message, dest=destLang, src=srcLang)
    return response.text

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

client.run(TOKEN)
