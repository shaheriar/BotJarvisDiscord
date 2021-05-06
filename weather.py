import requests
import json
import secretvars

ss = secretvars.secretvars()
weatherkey = ss.weatherkey
base_url = "http://api.openweathermap.org/data/2.5/weather?"

async def wthr(message):
    words = message.content
    important_words = words[8:]
    city_name = important_words
    complete_url = base_url + "appid=" + weatherkey + "&units=imperial" + "&q=" + city_name
    response = requests.get(complete_url)
    x = response.json()
    if x["cod"] != "404":
        # store the value of "main" 
        # key in variable y 
        y = x["main"] 
      
        # store the value corresponding 
        # to the "temp" key of y 
        current_temperature = y["temp"] 
      
        # store the value corresponding 
        # to the "pressure" key of y 
        current_pressure = y["pressure"] 
      
        # store the value corresponding 
        # to the "humidity" key of y 
        current_humidity = y["humidity"] 
      
        # store the value of "weather" 
        # key in variable z 
        z = x["weather"]
        f = current_temperature
        f = round(f,0)
        #city_name = city_name.capitalize()
      
        # store the value corresponding  
        # to the "description" key at  
        # the 0th index of z 
        weather_description = '**Weather for' + city_name.title() + ':**' + '\n"' + z[0]["main"] + '" with a temperature of ' + str(f) + '°F and humidity ' + str(current_humidity) + '%'
        await message.channel.send(weather_description)
    else:
        await message.channel.send('City not found')
