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
    try:
        # store the value of "main" 
        # key in variable current 
        current = data["current"]
        forecast = data['forecast']
        forecastday = forecast['forecastday'][0]['day']
        astro = forecast['forecastday'][0]['astro']

        condition = current["condition"]

        embed=discord.Embed(title=data["location"]["name"]+', '+data["location"]["region"]+', '+data["location"]["country"]+'\t')

        # Temperature
        embed.add_field(name='Temperature', value=str(current["temp_f"])+'°F', inline=False)

        # Humidity
        embed.add_field(name='Humidity', value=str(current['humidity'])+'%', inline=False)

        # Feels like
        embed.add_field(name='Feels Like', value=str(current['feelslike_f'])+'°F', inline=False)

        # High Temperature
        embed.add_field(name='High', value=str(forecastday['maxtemp_f'])+'°F', inline=True)

        # Low Temperature
        embed.add_field(name='Low', value=str(forecastday['mintemp_f'])+'°F', inline=True)

        # Chance of Rain
        embed.add_field(name='Chance of Rain', value=str(forecastday['daily_chance_of_rain'])+'%', inline=True)
        
        # Wind Speed
        embed.add_field(name='Wind Speed', value=str(current['wind_mph'])+'mph', inline=True)

        # Wind Direction
        embed.add_field(name='Wind Direction', value=current['wind_dir'], inline=True)

        # Pressure
        embed.add_field(name='Pressure', value=str(current['pressure_in'])+' in', inline=True)
        
        # UV Index
        embed.add_field(name='UV Index', value=current['uv'], inline=True)

        # Sunrise time
        embed.add_field(name='Sunrise', value=astro['sunrise'], inline=True)

        #Sunset Time
        embed.add_field(name='Sunset', value=astro['sunset'], inline=True)
        
        # When the weather data was recorded
        embed.set_footer(text='Last updated at '+current['last_updated'])

        # Weather condition icon
        embed.set_thumbnail(url='https:'+condition['icon'])
        
        await ctx.send(embed=embed)
    except:
        await ctx.send('City not found')
