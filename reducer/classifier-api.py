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
cur.execute("""SELECT SUM(count) FROM reductions_to_count_tmp""")
num_reductions = cur.fetchone()[0]

CORRECT_THRESHOLD = 0.00005 #TODO: Improve this threshold

@app.route("/", methods=["GET"])
def hello():
    sentence = request.args['sentence']
    print("Sentence: ", sentence)
    reductions = get_reduction(sentence, predictor)
    reduction_counts = [get_count(r) for r in reductions]
    correct = False
    if reduction_counts:
        correct = all([cnt > CORRECT_THRESHOLD for cnt in reduction_counts])
    correct_str = "CORRECT" if correct else "INCORRECT"
    return str(reductions) + "\n" + str(reduction_counts) + "\n" + correct_str

def get_count(reduction):
    cur.execute("""SELECT count FROM reductions_to_count_tmp WHERE
                    reduction=%s""", (reduction, ))
    row = cur.fetchone()
    return row[0]/num_reductions if row else 0
