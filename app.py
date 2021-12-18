from flask import Flask
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
import os
import spacy
from spacy.cli.download import download
download(model="en")

app = Flask(__name__)
chatterbot = ChatBot("Jarvis",
                     storage_adapter="chatterbot.storage.SQLStorageAdapter",
                     read_only=False,
                     database_uri=os.environ['DATABASE_URL']
                     )


# To train with default english corpus

# chatterbot.set_trainer(ChatterBotCorpusTrainer)

# chatterbot.train(
#     "chatterbot.corpus.english"
# )


# Create a new trainer for the chatbot
trainer = ChatterBotCorpusTrainer(chatterbot)

# Train the chatbot based on the english corpus
trainer.train(
    "chatterbot.corpus.english.ai",
"chatterbot.corpus.english.botprofile",
"chatterbot.corpus.english.computers",
"chatterbot.corpus.english.conversations",
"chatterbot.corpus.english.emotion",
"chatterbot.corpus.english.food",
"chatterbot.corpus.english.greetings",
"chatterbot.corpus.english.health",
"chatterbot.corpus.english.money",
"chatterbot.corpus.english.psychology",
)

###

@app.route('/chatter/<phrase>', methods=['GET'])
def note_page(phrase):
    try:
        response = str((chatterbot.get_response(phrase)))
        return(response)
    except:
        return("error getting response")


if __name__ == '__main__':
    app.run(debug=True)
