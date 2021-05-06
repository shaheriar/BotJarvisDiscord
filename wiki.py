import wikipedia
import requests
import json

def wiki_define(arg):
    try:
        url = r'https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&titles='+wikipedia.search(arg, results=1, suggestion=False)[0]+'&pithumbsize=500&format=json'
        req = requests.get(url)
        getj = json.loads(req.text)
        try:
            img = list(getj["query"]["pages"].values())[0]["thumbnail"]["source"]
        except KeyError:
            img = ' '
        definition = wikipedia.summary(arg, sentences=1, chars=100, 
        auto_suggest=False, redirect=True)+'\n'+img
    except wikipedia.exceptions.PageError:
        err = '`'+wiki_search(arg)+'`'
        definition = '**Error: Page not found**\n__Did you mean:__\n'+err
    except wikipedia.exceptions.DisambiguationError:
        err = '`'+wiki_search(arg)+'`'
        definition = '__Did you mean:__\n'+err
    except wikipedia.exceptions.WikipediaException:
        return
    return definition

def wiki_summary(arg):
    try:
        url = r'https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&titles='+wikipedia.search(arg, results=1, suggestion=False)[0]+'&pithumbsize=500&format=json'
        req = requests.get(url)
        getj = json.loads(req.text)
        try:
            img = list(getj["query"]["pages"].values())[0]["thumbnail"]["source"]
        except KeyError:
            img = ' '
        definition = wikipedia.summary(arg, sentences=5, chars=1000, 
        auto_suggest=False, redirect=True)+'\n'+img
    except wikipedia.exceptions.PageError:
        err = '`'+wiki_search(arg)+'`'
        definition = '**Error: Page not found**\n__Did you mean:__\n'+err
    except wikipedia.exceptions.DisambiguationError:
        err = '`'+wiki_search(arg)+'`'
        definition = '__Did you mean:__\n'+err
    except wikipedia.exceptions.WikipediaException:
        return
    return definition

def wiki_search(arg):
    print(wikipedia.search(arg, results=10, suggestion=False))
    results = wikipedia.search(arg, results=10, suggestion=False)
    rslt = '\n'.join(results)
    return rslt
