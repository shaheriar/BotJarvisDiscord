import requests
import json
import secretvars

ss = secretvars.secretvars()
weatherkey = ss.weatherkey
base_url = "https://api.weatherapi.com/v1/current.json?key="

async def wthr(ctx):
    words = ctx.message.content
    important_words = words[8:]
    city_name = important_words
    complete_url = base_url + weatherkey + '&q=' + city_name + '&aqi=no'
    response = requests.get(complete_url)
    x = response.json()
    if response.status_code != 404:
        # store the value of "main" 
        # key in variable y 
        y = x["current"] 
      
        # store the value corresponding 
        # to the "temp" key of y 
        current_temperature = y["temp_f"] 
      
        # store the value corresponding 
        # to the "humidity" key of y 
        current_humidity = y["humidity"] 
      
        # store the value of "weather" 
        # key in variable z 
        z = y["condition"]
        f = current_temperature
      
        # store the value corresponding  
        # to the "description" key at  
        # the 0th index of z 
        weather_description = '**' + x["location"]["name"] + ', ' + x["location"]["region"] + ', ' + x["location"]["country"] + ':**' + '\n"' + z["text"] + '" with a temperature of ' + str(f) + '°F and humidity ' + str(current_humidity) + '%'
        await ctx.send(weather_description)
    else:
        await ctx.send('City not found')
