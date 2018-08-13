#TODO: Move this file to another folder
from flask import Flask
from flask import request
from reducer_helper import get_reduction, load_predictor
import psycopg2
import os

app = Flask(__name__)

# Connect to the database
try:
    DB_NAME = os.environ.get('SVA_DB_NAME', 'sva')
    DB_PASSWORD = os.environ.get('SVA_DB_PASS', '')
    DB_USER = os.environ.get('SVA_DB_USER', 'etang')
except KeyError as e:
    print('important environment variables were not set')
    raise Exception('Warning: Important environment variables were not set')

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host='localhost')
cur = conn.cursor()

predictor = load_predictor(path="elmo-constituency-parser-2018.03.14.tar.gz")

@app.route("/", methods=["GET"])
def hello():
    sentence = request.args['sentence']
    print("Sentence: ", sentence)
    reductions = get_reduction(sentence, predictor)
    return str([get_count(r) for r in reductions])

def get_count(reduction):
    cur.execute("""SELECT count FROM reductions_to_count_tmp WHERE
                    reduction=%s""", (reduction, ))
    row = cur.fetchone()
    return row[0] if row else 0
