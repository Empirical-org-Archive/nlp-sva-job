#TODO: Move this file to another folder
from reducer_helper import get_reduction, load_predictor
import psycopg2
import os
from pattern.en import conjugate,tenses
import textacy

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

predictor = load_predictor(path="/var/lib/allennlp/elmo-constituency-parser-2018.03.14.tar.gz")
cur.execute("""SELECT SUM(count) FROM reductions_to_count_tmp""")
num_reductions = cur.fetchone()[0]


class Feedback(object):
    """Result feedback class"""
    def __init__(self):
        self.human_readable = '' # human readable advice
        self.primary_error = None
        self.specific_error = None
        self.matches = {}        # possible errors

    def to_dict(self):
        return self.__dict__

    def __repr__(self):
        return self.human_readable

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

def get_feedback(sentence):
    result = Feedback()
    alt_sentences = get_alt_sentences(sentence)
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

    if not correct:
        result.human_readable = "Incorrect -- suggestion: {}".format(suggestion)
        result.primary_error = 'SUBJECT_VERB_AGREEMENT_PRIMARY_ERROR'
        result.specific_error = 'SUBJECT_VERB_AGREEMENT_SPECIFIC_ERROR'
    else:
        result.human_readable = "Correct -- no subject verb agreement error found"
        result.primary_error = 'NONE'
        result.specific_error = 'NONE'
    return result

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