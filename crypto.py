import requests
import json
import secretvars
import discord
from datetime import datetime

ss = secretvars.secretvars()
weatherkey = ss.weatherkey
base_url = "https://data.messari.io/api/v1/assets"

async def crypto(ctx):
    words = ctx.message.content
    try:
        query = words.split('!crypto ')[1]
    except:
        query = ''
    response = requests.get(base_url)
    data = response.json()
    try:
        if (query == ''):
            embed=discord.Embed(title='Cryptocurrency Market Today')
            # Temperature
            for x in data['data']:
                name = x['name']
                symbol = x['symbol']
                price = x['metrics']['market_data']['price_usd']
                embed.add_field(name=name + ' ('+symbol+')', value='$'+str(round(price,5)), inline=True)
            embed.set_footer(text=datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
            await ctx.send(embed=embed)
        else:
            response = requests.get(base_url+'/'+query+'/metrics')
            data = response.json()
            name = data['data']['name']
            symbol = data['data']['symbol']
            market = data['data']['market_data']
            price = market['price_usd']

            embed=discord.Embed(title='Market data for ' + name + ' (' + symbol + ')')

            embed.add_field(name='Price',value='$'+str(round(price,5)),inline=False)


            embed.add_field(name='Last 1 Hour',value='-----------------------------------------------',inline=False)

            embed.add_field(name='Open',value='$'+str(round(market['ohlcv_last_1_hour']['open'],5)),inline=True)
            embed.add_field(name='High',value='$'+str(round(market['ohlcv_last_1_hour']['high'],5)),inline=True)
            embed.add_field(name='Low',value='$'+str(round(market['ohlcv_last_1_hour']['low'],5)),inline=True)
            embed.add_field(name='Close',value='$'+str(round(market['ohlcv_last_1_hour']['close'],5)),inline=True)
            

            embed.add_field(name='Last 24 Hours',value='-----------------------------------------------',inline=False)

            embed.add_field(name='Open',value='$'+str(round(market['ohlcv_last_24_hour']['open'],5)),inline=True)
            embed.add_field(name='High',value='$'+str(round(market['ohlcv_last_24_hour']['high'],5)),inline=True)
            embed.add_field(name='Low',value='$'+str(round(market['ohlcv_last_24_hour']['low'],5)),inline=True)
            embed.add_field(name='Close',value='$'+str(round(market['ohlcv_last_24_hour']['close'],5)),inline=True)
            
            
            embed.set_footer(text=datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
            await ctx.send(embed=embed)
    except:
        embed=discord.Embed(title='Error',description='Could not load data')
        await ctx.send(embed=embed)
