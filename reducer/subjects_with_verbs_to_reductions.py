import json
from collections import Counter
from pattern.en import mood

TEST_DATA='../test/data/sentences.json'


def get_mood(sentence):
    """Returns mood of sentence string"""
    conditional_words = ["assuming", "if", "in case", "no matter how",
            "supposing", "unless", "would", "'d", "should", "could",
            "might", "going to", "whenever", "as long as", "because",
            "in order to"
            ]
    result = mood(sentence)
    if result == 'imperative':
        return 'nonconditional' 
    if result in ['subjunctive', 'conditional']:
        for cw in conditional_words:
            if cw in sentence.lower():
                return 'conditional'
    return 'nonconditional' # indicative


def get_reduction(subject_with_verb, sentence):
    result = "{m}-{vp}>{np}"
    mood = get_mood(sentence).upper()
    return 'FAKE_RED'

def test_get_mood():
    with open(TEST_DATA) as f:
        test_dict = json.load(f)
    for sentence_obj in test_dict['sentences']:
        expected_reductions = Counter(sentence_obj['reductions']) # order doesn't matter
        subjects_with_verbs = sentence_obj['subjects_with_verbs']
        sent = sentence_obj['text']
        if sentence_obj['reductions']:
            m = get_mood(sent).upper()
            rm = sentence_obj['reductions'][0].split('-')[0]
        else:
            continue
        if m != rm:
            print(sent)
            print('mood guess, {}, real mood, {}'.format(m, rm))
    return None

def test():
    with open(TEST_DATA) as f:
        test_dict = json.load(f)
    for sentence_obj in test_dict['sentences']:
        expected_reductions = Counter(sentence_obj['reductions']) # order doesn't matter
        subjects_with_verbs = sentence_obj['subjects_with_verbs']
        print (sentence_obj['text'])
        ex, unex = [],[] 
        for swv in subjects_with_verbs:
            r = get_reduction(swv, sentence)
            if r in expected_reductions and expected_reductions[r] > 0:
                ex.append(r)
                expected_reductions[r] -= 1
            else:
                unex.append(r)
        unmatched = [unm for unm in expected_reductions if
                expected_reductions[unm] > 0]
        print('Found {} expected and {} unexpected reductions'.format(len(ex),
            len(unex)))
        print('unexpected:')
        for u in unex:
            print(u)
        print('unmatched:')
        for unm in unmatched:
            print(unm)
    return None

#test()
test_get_mood()

