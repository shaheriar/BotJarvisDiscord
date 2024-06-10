import wikipedia
import requests
import json
import discord

def wiki_define(arg):
    arg = arg.strip()
    try:  
        title = wikipedia.search(arg, suggestion=True)
        page = wikipedia.page(title=title[0][0], auto_suggest=False)
        
        url = r'https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&titles='+title[0][0]+'&pithumbsize=500&format=json'
        req = requests.get(url)
        getj = json.loads(req.text)
        
        try:
            img = list(getj["query"]["pages"].values())[0]["thumbnail"]["source"]
        except KeyError:
            img = ''
        
        embed = discord.Embed(title=title[0][0])
        
        if (img != ''):
            embed.set_thumbnail(url=img)
        
        print(page.summary.split('\n')[0])
        
        summary = page.summary.split('\n')[0]
        
        embed.add_field(name='Summary', value=summary, inline=False)
        
        return embed
    
    except wikipedia.exceptions.DisambiguationError as e:
        print("Ambiguous query: ",e.options)
        new_query = e.options[0]
        url = r'https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&titles='+new_query+'&pithumbsize=500&format=json'
        req = requests.get(url)
        getj = json.loads(req.text)
        
        try:
            img = list(getj["query"]["pages"].values())[0]["thumbnail"]["source"]
        except KeyError:
            img = ''
            
        page = wikipedia.page(title=new_query, auto_suggest=False)
        
        embed=discord.Embed(title=new_query)
        
        if (img != ''):
            embed.set_thumbnail(url=img)
            
        embed.add_field(name='Summary', value=page.summary.split('\n')[0], inline=False)
        
        return embed
    
    except wikipedia.exceptions.PageError as e:
        embed=discord.Embed(title=arg)
        embed.add_field(name='Error', value='Page not found', inline=False)
        return embed
        


def wiki_summary(arg):
    arg = arg.strip()
    try:  
        title = wikipedia.search(arg, suggestion=True)
        page = wikipedia.page(title=title[0][0], auto_suggest=False)
        
        url = r'https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&titles='+title[0][0]+'&pithumbsize=500&format=json'
        req = requests.get(url)
        getj = json.loads(req.text)
        
        try:
            img = list(getj["query"]["pages"].values())[0]["thumbnail"]["source"]
        except KeyError:
            img = ''
        
        embed = discord.Embed(title=title[0][0])
        
        if (img != ''):
            embed.set_thumbnail(url=img)
        
        print(page.summary.split('\n')[0])
        
        embed.add_field(name='Summary', value=page.summary.split('\n')[0], inline=False)
        
        return embed
    
    except wikipedia.exceptions.DisambiguationError as e:
        print("Ambiguous query: ",e.options)
        new_query = e.options[0]
        url = r'https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&titles='+new_query+'&pithumbsize=500&format=json'
        req = requests.get(url)
        getj = json.loads(req.text)
        
        try:
            img = list(getj["query"]["pages"].values())[0]["thumbnail"]["source"]
        except KeyError:
            img = ''
            
        page = wikipedia.page(title=new_query, auto_suggest=False)
        
        embed=discord.Embed(title=new_query)
        
        if (img != ''):
            embed.set_thumbnail(url=img)
            
        embed.add_field(name='Summary', value=page.summary.split('\n')[0], inline=False)
        
        return embed
    
    except wikipedia.exceptions.PageError as e:
        embed=discord.Embed(title=arg)
        embed.add_field(name='Error', value='Page not found', inline=False)
        return embed

def wiki_search(arg):
    print(wikipedia.search(arg, results=10, suggestion=False))
    results = wikipedia.search(arg, results=10, suggestion=False)
    rslt = '\n'.join(results)
    return rslt
