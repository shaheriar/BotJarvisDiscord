import requests
import json
import secretvars
import discord
from datetime import datetime

ss = secretvars.secretvars()
weatherkey = ss.weatherkey

async def stocks(ctx):
    
    words = ctx.message.content
    try:
        query = words.split('!stocks ')[1]
        base_url = "https://finnhub.io/api/v1/"
        token_url = "&token="+ss.stockskey
        search_url = base_url+'search?q='+query+token_url
        search = requests.get(search_url).json()['result'][0]
        info_url = base_url+'quote?symbol='+search['symbol']+token_url
        info = requests.get(info_url).json()
        logo = requests.get(base_url+'stock/profile2?symbol='+search['symbol']+token_url).json()['logo']
        embed = discord.Embed(title='Today\'s Stock Market Information for '+search['symbol'])
        
        embed.add_field(name='Name',value=search['description'],inline=False)
        embed.add_field(name='Current Price',value='$'+str(info['c']),inline=False)
        embed.add_field(name='Change',value='$'+str(info['d']),inline=True)
        embed.add_field(name='Percent Change',value=str(info['dp'])+'%',inline=True)
        
        embed.add_field(name='High',value='$'+str(info['h']),inline=True)
        embed.add_field(name='Low',value='$'+str(info['l']),inline=True)
        embed.add_field(name='Open',value='$'+str(info['o']),inline=True)
        
        embed.add_field(name='Previous Close Price',value='$'+str(info['pc']),inline=True)
        embed.set_footer(text=datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
        embed.set_thumbnail(url=logo)

        await ctx.send(embed=embed)

    except:
        await ctx.send(embed=discord.Embed(title='Error',description='Could not find any data under that name.'))
