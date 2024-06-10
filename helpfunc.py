def hlp():
    help = [
    '**HELP PAGE',
    '__LIST OF COMMANDS__**',
    '**!help** : Opens the help page',
    '**!define {word}** : Get a one sentence definition of anything',
    '**!summary {word}** : Get a more in depth definition of anything',
    '**!search {word}** : Search for keywords',
    '**!weather {city}** : Get weather info for any city',
    '**!crypto (optional){symbol}** : Get crypto information in general or about a specific currency',
    '**!stocks {stock}** : Get stock market information about a specific stock',
    '**!news {topic}** : Get a list of news you\'re searching for',
    '**!coin** : Flip a coin!',
    '**!8ball {text}** : Let the magic 8-Ball decide your fate',
    '**!dice** : Roll a dice and get a random number from 1 to 6',
    '**!invite** : Invite me to other servers!',
    '**!song {query}** : Search or paste a url to play a song in your voice channel',
    '**!leave** : Leave your voice channel',
    '**!pause** : Pause the current song',
    '**!resume** : Resume the current song',
    '**!stop** : Stop the current song'
    ]

    helptext = '\n'.join(help)
    return helptext
