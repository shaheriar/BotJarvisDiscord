def hlp():
    help = [
    '**HELP PAGE',
    '__LIST OF COMMANDS__**',
    '**!help** : Opens the help page',
    '**!weather {city}** : Get weather info for any city',
    '**!crypto (optional){symbol}** : Get crypto information in general or about a specific currency',
    '**!stocks {stock}** : Get stock market information about a specific stock',
    '**!coin** : Flip a coin!',
    '**!8ball {text}** : Let the magic 8-Ball decide your fate',
    '**!dice** : Roll a dice and get a random number from 1 to 6',
    '**!invite** : Invite me to other servers!',
    '**!jarvis {question}** or @Jarvis : Ask Jarvis anything (search, define, summarize, weather, stocks, crypto, etc.)'
    ]

    helptext = '\n'.join(help)
    return helptext
