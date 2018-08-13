#TODO: Move this file to another folder
from flask import Flask
from reducer_helper import get_reduction, load_predictor

app = Flask(__name__)

@app.route("/")
def hello():
    test_sent = "The Expo marker was a bland purple that triggered her intense synesthesia."
    print("Test sent:", test_sent)
    predictor = load_predictor(path="elmo-constituency-parser-2018.03.14.tar.gz")
    return str(get_reduction(test_sent, predictor))
