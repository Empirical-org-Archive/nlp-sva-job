#TODO: Move this file to another folder
from flask import Flask,jsonify
from flask import request
from reducer_helper import get_reduction, load_predictor
import psycopg2
import os
from pattern.en import conjugate,tenses
import textacy

app = Flask(__name__)

# Connect to the database
try:
    DB_NAME = os.environ.get('DB_NAME', 'sva')
    DB_PASSWORD = os.environ.get('DB_PASS', '')
    DB_USER = os.environ.get('DB_USER', 'etang')
except KeyError as e:
    print('important environment variables were not set')
    raise Exception('Warning: Important environment variables were not set')

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host='localhost')
cur = conn.cursor()

predictor = load_predictor(path="/var/lib/allennlp/elmo-constituency-parser-2018.03.14.tar.gz")
cur.execute("""SELECT SUM(count) FROM reductions_to_count_tmp""")
num_reductions = cur.fetchone()[0]

CORRECT_THRESHOLD = 0.00005 #TODO: Improve this threshold


def get_alt_sentences(sentence):
    d = textacy.Doc(sentence, lang='en_core_web_sm')
    alt_sentences = []
    for t in d:
        if t.tag_.startswith('VB'):
            tense, aspect = get_tense_and_aspect(t.text)
            if tense and aspect:
                new_word = conjugate(t.text, tense=tense, aspect=aspect,
                        number='singular', person=1)
                if new_word != t.text:
                    new_sentence = sentence[:t.idx] + new_word + sentence[t.idx+len(t.text):]
                    alt_sentences.append(new_sentence)
                new_word = conjugate(t.text, tense=tense, aspect=aspect,
                        number='plural', person=1)
                if new_word != t.text:
                    new_sentence = sentence[:t.idx] + new_word + sentence[t.idx+len(t.text):]
                    alt_sentences.append(new_sentence)
                # 2
                new_word = conjugate(t.text, tense=tense, aspect=aspect,
                        number='singular', person=2)
                if new_word != t.text:
                    new_sentence = sentence[:t.idx] + new_word + sentence[t.idx+len(t.text):]
                    alt_sentences.append(new_sentence)
                new_word = conjugate(t.text, tense=tense, aspect=aspect,
                        number='plural', person=2)
                if new_word != t.text:
                    new_sentence = sentence[:t.idx] + new_word + sentence[t.idx+len(t.text):]
                    alt_sentences.append(new_sentence)
                # 3
                new_word = conjugate(t.text, tense=tense, aspect=aspect,
                        number='singular', person=3)
                if new_word != t.text:
                    new_sentence = sentence[:t.idx] + new_word + sentence[t.idx+len(t.text):]
                    alt_sentences.append(new_sentence)
                new_word = conjugate(t.text, tense=tense, aspect=aspect,
                        number='plural', person=3)
                if new_word != t.text:
                    new_sentence = sentence[:t.idx] + new_word + sentence[t.idx+len(t.text):]
                    alt_sentences.append(new_sentence)
    return list(set(alt_sentences))


@app.route("/", methods=["GET"])
def hello():
    sentence = request.args['sentence']
    alt_sentences = get_alt_sentences(sentence)
    print("Sentence: ", sentence)
    print("Alt. Sentences: ")
    for alt_s in alt_sentences:
        print(" >" + alt_s)
    reductions = get_reduction(sentence, predictor)
    reduction_counts = [get_count(r) for r in reductions]
    score = sum(reduction_counts)
    alt_score = 0
    suggestion = "< no suggestion >"
    for alt_s in alt_sentences:
        areductions = get_reduction(alt_s, predictor)
        reduction_counts = [get_count(r) for r in areductions]
        if sum(reduction_counts) > alt_score:
            alt_score = sum(reduction_counts)
            suggestion = alt_s
    if alt_score > score:
        correct =  False
    elif score == 0:
        correct = False
    else:
        correct = True
        
    #correct = False
    #if reduction_counts:
    #    correct = all([cnt > CORRECT_THRESHOLD for cnt in reduction_counts])
    correct_str = "CORRECT" if correct else "INCORRECT"
    result = correct_str
    if not correct:
        result += '-- suggestion: {}'.format(suggestion)

    return jsonify(result)

def get_count(reduction):
    cur.execute("""SELECT count FROM reductions_to_count_tmp WHERE
                    reduction=%s""", (reduction, ))
    row = cur.fetchone()
    return row[0]/num_reductions if row else 0


def get_tense_and_aspect(verb):
    t = tenses(verb)
    for tx in t:
        if tx[0] and tx[4]:
            return (tx[0], tx[4])
    return (None, None)




if __name__ == '__main__':
    app.run(port=10300, host='0.0.0.0', debug=True)
