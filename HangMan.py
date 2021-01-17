import random
start = False
done = False
found = False
streak = False
strk = 1
cnt = 1
ind = 0
category = ""
movies = ['Joker','Parasite','1917','Avengers: Endgame','Klaus','Gully Boy','Ford v Ferrari','The Gentlemen','Little Women','Knives Out','The Shawshank Redemption','The Godfather','The Godfather: Part II','The Dark Knight','12 Angry Men',"Schindler's List",'Pulp Fiction','The Good, the Bad and the Ugly','The Lord of the Rings: The Return of the King','Fight Club','The Lord of the Rings: The Fellowship of the Ring','Star Wars: Episode V - The Empire Strikes Back','Forrest Gump','Inception','One Flew Over the Cuckoos Nest','The Lord of the Rings: The Two Towers','Goodfellas','The Matrix','Star Wars','Seven Samurai','City of God','The Silence of the Lambs','The Usual Suspects',"It's a Wonderful Life",'Life Is Beautiful','Once Upon a Time in the West','Interstellar','Saving Private Ryan','American History X','Spirited Away','Casablanca','Raiders of the Lost Ark','Psycho','City Lights','Rear Window','The Intouchables','Modern Times','Terminator 2: Judgment Day','Whiplash','The Green Mile','The Pianist','Memento','The Departed','Gladiator','Apocalypse Now','Back to the Future','Sunset Blvd.','The Prestige','Alien','The Lion King','The Lives of Others','The Great Dictator','Inside Out','Cinema Paradiso','The Shining','Paths of Glory','Django Unchained','The Dark Knight Rises','WALL-E','American Beauty','Grave of the Fireflies','Aliens','Citizen Kane','North by Northwest','Princess Mononoke','Vertigo','Oldeuboi','Das Boot','Star Wars: Episode VI - Return of the Jedi','Once Upon a Time in America','Witness for the Prosecution','Reservoir Dogs','Braveheart','Toy Story 3','A Clockwork Orange','Double Indemnity','Taxi Driver','Requiem for a Dream','To Kill a Mockingbird','Lawrence of Arabia','Eternal Sunshine of the Spotless Mind','Full Metal Jacket','The Sting','Amadeus','Bicycle Thieves','Singin in the Rain','Monty Python and the Holy Grail','Snatch.','2001: A Space Odyssey','The Kid','L.A. Confidential','For a Few Dollars More','Toy Story','The Apartment','Inglourious Basterds','All About Eve','The Treasure of the Sierra Madre','Jodaeiye Nader az Simin','Indiana Jones and the Last Crusade','Metropolis','Yojimbo','The Third Man','Batman Begins','Scarface','Some Like It Hot','Unforgiven','3 Idiots','Up','Raging Bull','Downfall','Mad Max: Fury Road','Jagten','Chinatown','The Great Escape','Die Hard','Good Will Hunting','Heat','On the Waterfront',"Pan's Labyrinth",'Mr. Smith Goes to Washington','The Bridge on the River Kwai','My Neighbor Totoro','Ran','The Gold Rush','Ikiru','The Seventh Seal','Blade Runner','The Secret in Their Eyes','Wild Strawberries','The General','Lock, Stock and Two Smoking Barrels','The Elephant Man','Casino','The Wolf of Wall Street',"Howl's Moving Castle",'Warrior','Gran Torino','V for Vendetta','The Big Lebowski','Rebecca','Judgment at Nuremberg','A Beautiful Mind','Cool Hand Luke','The Deer Hunter','How to Train Your Dragon','Gone with the Wind','Fargo','Trainspotting','It Happened One Night','Dial M for Murder','Into the Wild','Gone Girl','The Sixth Sense','Rush','Finding Nemo','The Maltese Falcon','Mary and Max','No Country for Old Men','The Thing','Incendies','Hotel Rwanda','Kill Bill: Vol. 1','Life of Brian','Platoon','The Wages of Fear','Butch Cassidy and the Sundance Kid','There Will Be Blood','Network','Touch of Evil','The 400 Blows','Stand by Me','12 Years a Slave','The Princess Bride','Annie Hall','Persona','The Grand Budapest Hotel','Amores Perros','In the Name of the Father','Million Dollar Baby','Ben-Hur','The Grapes of Wrath',"Hachi: A Dog's Tale",'Shutter Island','Diabolique','Sin City','The Wizard of Oz','Gandhi','Stalker','The Bourne Ultimatum','The Best Years of Our Lives','Donnie Darko','Relatos salvajes','Strangers on a Train','Jurassic Park','The Avengers','Before Sunrise','Twelve Monkeys','The Terminator','Infernal Affairs','Jaws','The Battle of Algiers','Groundhog Day','Memories of Murder','Guardians of the Galaxy','Monsters, Inc.','Harry Potter and the Deathly Hallows: Part 2','Throne of Blood','The Truman Show','Fanny and Alexander','Barry Lyndon','Rocky','Dog Day Afternoon','The Imitation Game','Yip Man',"The King's Speech",'High Noon','La Haine','A Fistful of Dollars','Pirates of the Caribbean: The Curse of the Black Pearl','Notorious','Castle in the Sky','Prisoners','The Help','Roman Holiday','The Night of the Hunter','Beauty and the Beast','La Strada','Papillon','X-Men: Days of Future Past','Before Sunset','Anatomy of a Murder','The Hustler','The Graduate','The Big Sleep','Underground','Elite Squad: The Enemy Within','Gangs of Wasseypur','Lagaan: Once Upon a Time in India','Akira','Black Hawk Down','Casino Royal','Collateral','Doctor Strange','John Wick','Skyfall','Taken','The Raid','Ratatouille','World of tomorrow','Zootopia','Hot Fuzz','Office Space','Shaun of the Dead','Superbad','The Big Short','The Breakfast Club','Ticker and Dale vs Evil','Tropic Thunder','127 Hours','American Psycho','Birdman','Black Swan','Blood Diamond','Call Me if You Can','Dallas Buyers Club','Dead Poets Society','Drive','Fantastic Beasts and Where to Find Them','Groundhog Day','Hugo','Leon: The Professional','Life of Pi','Machinist','Nightcrawler','Nocturnal Animals','Rain Man','Requiem For a Dream','Ruby Sparks','Samsara','Short Term 12','Sing Street','The Aviator','The Boy in the Striped Pyjamas','The Perks of Being a Wallflower','The Revenant','The Social Network','The Spectacular Now','Arrival','Chronicle','Edge of Tomorrow','Equilibrium','Ex Machina','Gravity','Her','Looper','Minority Report','Moon','Serenity','Source Code','Sunshine','The Martian','A Ghost Story','A Serious Man','Certified Copy','Mr. Nobody','Open Your Eyes','Synecdoche, New York','The Fountain','The Man From Earth','The Master','The Sunset Limited','To the Wonder','Tree of Life','Upstream Color','Waking life','Wings of Desire','28 Days Later',"Ocean's 8"]
stage = []
display = [] #v dislayed as you guess them
notfound = [] #nf list of chars gotten wrong
word = "" #nn the word selected
userIn = ""


def userInput(userIn):
    return userIn

def setup(input):
    global stage
    correct = False
    while not(correct):
        print("1. Movies\nPress 1 to Start: ")
        arg = int(input)
        correct = True
        def switch_demo(arg):
            def invalid():
                correct = False
                return "Invalid entry, Try again"
            switcher = {
                1: random.choice(movies)  
            }
            return switcher.get(arg, invalid)
    stage = ["_______\n|     |\n|      \n|      \n|      \n|       \n|__________\n", "_______\n|     |\n|     O\n|      \n|      \n|       \n|__________\n", "_______\n|     |\n|     O\n|     |\\\n|      \n|       \n|__________\n", "_______\n|     |\n|     O\n|    /|\\\n|      \n|       \n|__________\n", "_______\n|     |\n|     O\n|    /|\\\n|     |\n|      \\\n|__________\n", "_______\n|     |\n|     O\n|    /|\\\n|     |\n|    / \\\n|__________\n"]
    return switch_demo(arg)

#print(setup("2"))

def lost():
    if ind > 4:
        return True
    return False

def isDone():
    for x in display:
        if x == '_':
            return False
        
    return True

def notFound(inn):
    f = False
    for c in notfound:
        if c == inn:
            f = True

    if not f:
        notfound.append(inn)

def printOut():
    global ind
    global word
    print("\n-- H A N G  M A N --\n")
    print(stage[ind], "\n")
    c = ' '.join(display)
    print(c)
    print("\n")

    c = ' '.join(notfound)
    print(c, "\n")

    if not found and start:
        print("\nOops! Letter not found\n")
    elif found and start:
        print("\nLetter found!\n")

    if lost():
        print("\n-- G A M E  L O S T --\n\nThe word was: ", word, "\n")
    elif isDone():
        print("\n-- W O R D  G U E S S E D! --\n")
        print("\nGuesses left: ", 5-ind, "\n")

    print("\nTries left: ", 5-ind)

def isSpecialChar(c):
    if c == ' ' or c == ':' or c == '\'' or c == ',' or c == '-' or c == '.':
        return True
    return False

def play():
    global done
    global ind
    global notfound
    global word
    newGame = True
    choice = ''
    word = setup("1")
    while newGame:
        word.lower()
        r = random.choice(word)
        if(isSpecialChar(r)):
            while isSpecialChar(r):
                r = random.choice(word)

        for c in word:
            if r == c:
                display.append(c)
            elif isSpecialChar(c):
                display.append(c)
            else:
                display.append('_')
        while not done:
            printOut()
            print("\nGuess one letter of the word: ")
            found = False;
            guess = input() #replace for discord input
            index = 0;
            for c in word:
                if guess == c.lower():
                    display[index] = c
                    found = True
                index += 1

            if not found:
                ind += 1
                notFound(guess)
            done = isDone() or lost()
            start = True

        printOut()
        choice = input("\nNew Game? (Y/N): ")
        if(choice.lower() != 'y' and choice.lower() != 'n'):
            while (choice.lower() != 'y' and choice.lower() != 'n'):
                choice = input("\nPlease enter either Y or N: ")
                print("\n")

        if choice.lower() == 'y':
            newGame = True
            display.clear()
            notfound.clear()
            word = setup("1")
            ind = 0
            done = False
            start = False
        elif choice.lower() == 'n':
            break
