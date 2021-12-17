import requests
import json
import secretvars
import discord

ss = secretvars.secretvars()
weatherkey = ss.weatherkey
base_url = "https://api.weatherapi.com/v1/forecast.json?key="

async def wthr(ctx):
    words = ctx.message.content
    important_words = words[8:]
    city_name = important_words
    complete_url = base_url + weatherkey + '&q=' + city_name + '&aqi=no'
    print(complete_url)
    response = requests.get(complete_url)
    data = response.json()
    if response.status_code != 404:
        # store the value of "main" 
        # key in variable current 
        current = data["current"]
        forecast = data['forecast']
        forecastday = forecast['forecastday'][0]['day']
        astro = forecast['forecastday'][0]['astro']

        condition = current["condition"]

        embed=discord.Embed(title=data["location"]["name"]+', '+data["location"]["region"]+', '+data["location"]["country"]+'\t')
        embed.add_field(name='Temperature', value=str(current["temp_f"])+'°F', inline=False)
        embed.add_field(name='Humidity', value=str(current['humidity'])+'%', inline=False)
        embed.add_field(name='Feels Like', value=str(current['feelslike_f'])+'°F', inline=False)

        embed.add_field(name='High', value=str(forecastday['maxtemp_f'])+'°F', inline=True)
        embed.add_field(name='Low', value=str(forecastday['mintemp_f'])+'°F', inline=True)
        embed.add_field(name='Chance of Rain', value=str(forecastday['daily_chance_of_rain'])+'%', inline=True)

        embed.add_field(name='Wind Speed', value=str(current['wind_mph'])+'mph', inline=True)
        embed.add_field(name='Wind Direction', value=current['wind_dir'], inline=True)
        embed.add_field(name='Pressure', value=str(current['pressure_in'])+' in', inline=True)
        
        embed.add_field(name='UV Index', value=current['uv'], inline=True)
        embed.add_field(name='Sunrise', value=astro['sunrise'], inline=True)
        embed.add_field(name='Sunset', value=astro['sunset'], inline=True)
        
        embed.set_footer(text='Last updated at '+current['last_updated'])
        embed.set_thumbnail(url='https:'+condition['icon'])
        
        # store the value corresponding  
        # to the "description" key at  
        # the 0th index of condition 
        await ctx.send(embed=embed)
    else:
        await ctx.send('City not found')
