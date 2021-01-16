def parseForTans(input):
    parsedWordArray = input.split(' ', 3)
    parsedWordArray.remove(".t")
    return parsedWordArray



test = parseForTans(".t hello my name is Ryan")
print(test)