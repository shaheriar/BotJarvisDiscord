def parseForTrans(input):
    parsedWordArray = input[3:].split(' ', 2)
    return parsedWordArray

test = parseForTrans("!t en pa water is good")
print(test)