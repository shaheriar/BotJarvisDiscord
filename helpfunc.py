def hlp():
    help = ['**HELP PAGE\n',
    '__LIST OF COMMANDS__**\n',
    '**!help** : Opens the help page\n',
    '**!define {word}** : Get a one sentence definition of anything\n',
    '**!summary {word}** : Get a more in depth definition of anything\n',
    '**!search {word}** : Search for keywords\n',
    '**!weather {city}** : Get weather info for any city\n',
    '**!crypto (optional){symbol}** : Get crypto information in general or about a specific currency\n',
    '**!stocks {stock}** : Get stock market information about a specific stock\n',
    '**!t {source} {destination} {text}** : Translate anything from source language to destination language\n',
    '**!langs** : Get a list of supported languages to translate\n',
    '**!news {topic}** : Get a list of news you\'re searching for\n',
    '**!coin** : Flip a coin!\n',
    '**!8ball {text}** : Let the magic 8-Ball decide your fate\n',
    '**!dice** : Roll a dice and get a random number from 1 to 6\n',
    '**!reddit {subreddit}** : Get the top 5 posts in a subreddit\n',
    '**!invite** : Invite me to other servers!\n',
    '**!song {query}** : Search or paste a url to play a song in your voice channel\n',
    '**!leave** : Leave your voice channel\n',
    '**!pause** : Pause the current song\n',
    '**!resume** : Resume the current song\n',
    '**!stop** : Stop the current song\n',
    '**!stats {username#tag}** : Get Valorant stats for any player who has an account on tracker.gg\n'
    ]

    helptext = ''.join(help)
    return helptext
