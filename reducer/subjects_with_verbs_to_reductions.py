import json
from collections import Counter
from pattern.en import mood,lemma,tenses
from hashlib import sha256
import top100

TEST_DATA='../test/data/sentences.json'

def get_verb_reduction(verb, tag):
    """Given string of existing verb, returns its corresponding reduction
    That's the verb itself if its lemma is in the top100, else its hash"""
    if lemma(verb.lower()) in top100.verbs:
        return verb.upper()
    else:
        h = sha256(str(tenses(verb)).encode('utf_8')).hexdigest()
        result = tag + '_' + h
        return result


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
        return 'subjunctive'
    return 'nonconditional' # indicative

def get_verb_phrase_reduction(verb_phrase_word_list):
    rl = [get_verb_reduction(vpw['word'], vpw['label']) for vpw in
            verb_phrase_word_list]
    return ':'.join(rl)

def get_noun_phrase_reduction(noun_phrase_word_list):
    # SG, list length is 1 singular noun
    if (len(noun_phrase_word_list) == 1 and noun_phrase_word_list[0]['label'] in
            ['NN', 'NNP']):
    
        
    # take care of single words
    NNS -> PL, NN -> SG, NNP -> SG, NNPS -> PL 
    # noun phrase can be
    # an array of 


def get_reduction(subject_with_verb, sentence):
    result = "{m}-{vp}>{np}"
    m = get_mood(sentence).upper()
    vp = get_verb_phrase_reduction(subjects_with_verb['vp'])
    np = get_noun_phrase_reduction(subject_with_verb['np'])
    return 'FAKE_RED'

#########################

def test_get_verb_phrase_reduction():
    with open(TEST_DATA) as f:
        test_dict = json.load(f)
    for sentence_obj in test_dict['sentences']:
        expected_reductions = Counter(sentence_obj['reductions']) # order doesn't matter
        subjects_with_verbs = sentence_obj['subjects_with_verbs']
        print (sentence_obj['text'])
        ex, unex = [],[] 
        for swv in subjects_with_verbs:
            vpr = get_verb_phrase_reduction(swv['vp'])
            print(vpr)


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
#test_get_mood()
test_get_verb_phrase_reduction()

