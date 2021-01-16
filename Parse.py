def parseForTans(input):
    parsedWordArray = input.split(' ', 3)
    parsedWordArray.pop(0)
    return parsedWordArray



test = parseForTans(".t hello my name is Ryan")
print(test)