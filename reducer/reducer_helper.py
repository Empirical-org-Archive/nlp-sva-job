from allennlp.service.predictors import Predictor
from nltk.tree import Tree
from preprocess import preprocess_sent
from pattern.en import mood, tenses, lemma
from hashlib import sha256
import top100

import json

def load_predictor():
    """Load model from AllenNLP, which we've downloaded"""
    return Predictor.from_path("elmo-constituency-parser-2018.03.14.tar.gz")

def get_verb_subject_pairs(tree):
    """ Returns the individual words associated with each verb and noun phraseself.

    Will soon return pairs in the format:
    { ‘sentence’: [{‘vp’: [ {‘word’: ‘has’, ‘label’: ‘VBZ’},  {‘word’: ‘been’, ‘label’: ‘VBG’ }, { ‘word’: ‘owed’, ‘label’: ‘VBZ’ } ],
                    ‘np’: [ { ‘word’: ‘so’, ‘label’: ‘DT’ }, { ‘word’: ‘much’, ‘label’: ‘PN’ }] },  ….  ] }
    """
    pairs = get_verb_subject_phrases(tree)
    words = {'subjects_with_verbs': []}
    for pair in pairs['subjects_with_verbs']:
        np = pair['np']
        vp = pair['vp']
        words['subjects_with_verbs'].append({'vp': verb_words_from_phrase(vp), 'np': subject_words_from_phrase(np)})
    return words


def get_verb_subject_phrases(tree):
    """
    Returns pairs in the format:
    { 'subjects_with_verbs': [{'vp': Tree(Verb phrase), 'np': Tree(Noun phrase)}, {'vp': Tree(second verb phrase), 'np': Tree(second noun phrase)}, ...] }
    """
    pairs = []

    # Declarative clause:
    for s in tree.subtrees(lambda t: t.label() == 'S'):
        pairs += verb_subject_for_declarative_clause(s)

    # "Direct question introduced by a wh-word or a wh-phrase"
    for sbarq in tree.subtrees(lambda t: t.label() == 'SBARQ'):
        pairs += verb_subject_for_sbarq(sbarq)

    return { 'subjects_with_verbs': pairs }

# MARK: Extracting pairs from various clauses:

def verb_subject_for_declarative_clause(tree):
    """ Takes in the tree for a vanilla declarative clause (S tag)
        Returns list of subject, verb pairs, empty if none
    """
    np = None
    vps = []
    for i in range(0, len(tree)):
        child = tree[i]
        np = child if child.label() == "NP" else np
        vps += [child] if child.label() == "VP" else []

    print("vps before unpacking", vps)
    vps = sum([unpack_verb_phrases(vp) for vp in vps], [])
    print("vps after unpacking", vps)
    if np is not None:
        # TODO: Under what circumstances should we return one of these having a None value?
        return [{ 'vp': vp, 'np': np } for vp in vps]
    return []


def verb_subject_for_sbarq(tree):
    """
    Takes tree for a SBARQ clause: question introduced by a wh-word or a wh-phrase
    Returns list of subject, verb pairs, empty if none
    """
    wh_words = ["WHADJP", "WHAVP", "WHNP", "WHPP"]
    for i in range(0, len(tree) - 1):
        # Identify the wh-word and the possible subsequent SQ
        phrase = tree[i]
        next_phrase = tree[i + 1]
        if phrase.label() in wh_words and next_phrase.label() == 'SQ':
            return [{ 'vp': next_phrase, 'np': phrase}]
    return []


# MARK: Helper functions for extracting pairs

def unpack_verb_phrases(vp):
    """
    If there are MULTIPLE verb phrases nested within the verb phrase, returns these
    Otherwise, returns a list with the original verb phrase
    """
    child_phrases = [child for child in vp if child.label() == 'VP']
    return child_phrases if len(child_phrases) > 1 else [vp]



def print_verb_subject_phrases(pairs):
    """Print verb_subject pairs in readable form"""
    print("Verb Subject Pairs: ")
    for pair in pairs['subjects_with_verbs']:
        print("Noun Phrase: ", ' '.join(pair['np'].leaves()) if type(pair['np']) is Tree else "None")
        print("Verb Phrase: ", ' '.join(pair['vp'].leaves()) if type(pair['vp']) is Tree else "None")



# MARK: SUBJECTS


def subject_words_from_phrase(subject):
    """
    Given subject phrase as a tree, returns list of relevant nouns with labels
    """

    pronoun_tags = ["PRP", "PRP$", "WP", "WP$"]
    singular_tags = ["NN", "NNP"]
    plural_tags = ["NNS", "NNPS"]
    wh_tags = ["WHADJP", "WHAVP", "WHNP", "WHPP"]
    noun_tags = pronoun_tags + singular_tags + plural_tags + wh_tags

    words = []
    if subject is None: # No subject
        return words
    else:
        # Otherwise, return a list of the nouns
        for i in range(0, len(subject)):
            child = subject[i]
            if child.label() == "NP": # Recursively identify sub-phrases
                words += subject_words_from_phrase(child)
            if child.label() in noun_tags:
                words.append({'word': child[0], 'label': child.label()})
    return words


# MARK: Verbs


def verb_words_from_phrase(vp):
    "Given a verb phrase, returns a list of the verb reductions"
    verb_tags = ["MD", "VB", "VBZ", "VBP", "VBD", "VBN", "VBG"]

    if vp is None:
        return []

    words = []
    for i in range(0, len(vp)):
        child = vp[i]
        if child.label() in verb_tags:
            words.append( { 'word': child[0], 'label': child.label() })
        if child.label() == "VP":
            words += verb_words_from_phrase(child)
    return words


def sentence_to_pairs(sent, predictor):
    """ Takes a sentence and AllenNLP predictor, returns the subject_verb pairs
    """
    processed = preprocess_sent(sent)
    parse = predictor.predict_json({"sentence": processed})
    tree = Tree.fromstring(parse["trees"])
    return {
        'subjects_with_verbs': get_verb_subject_pairs(tree),
        'text': sent
    }

# MARK: Test Sentences and Pipeline

def test_pipeline(sent, predictor):
    """
    Test and log whole pipeline, from sentence to reductions
    Takes sentence and AllenNLP predictor
    Current pipeline: preprocess, AllenNLP parse, verb_subject pair extraction,
    verb phrase extraction, noun phrase extraction, mood
    """
    print("Original Sentence: ", sent)
    sent = preprocess_sent(sent)
    print("Processed Sentence: ", sent)
    parse = predictor.predict_json({"sentence": sent})
    tree = Tree.fromstring(parse["trees"])
    print("Tree: \n", tree)
    pairs = get_verb_subject_phrases(tree)
    print_verb_subject_phrases(pairs)

    for pair in pairs['subjects_with_verbs']:
        subject = pair['np']
        print(subject_words_from_phrase(subject))
        vp = pair['vp']
        print(verb_words_from_phrase(vp))

    pairs = get_verb_subject_pairs(tree)
    print(pairs)
    return pairs

def evaluate_subjects_with_verbs(actual, expected):
    """ Evaluates two given subjects_with_verbs object to check their equality, prints """
    # We do some really tedious checking here because sorting this list of
    # dictionaries is otherwise sorta annoying
    equal = True
    for pair in actual:
        if pair not in expected:
            equal = False
    for pair in expected:
        if pair not in actual:
            equal = False

    if equal:
        print("PASSED $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ ")
        return 1
    else:
        print("MISMATCH !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! ")
        print("Expected:", expected)
        print("Got:", actual)
        return 0

# MARK: Test Script

with open('../test/data/sentences.json') as test_file:
    tests = json.load(test_file)

test_sents = [(example["text"], example["subjects_with_verbs"]) for example in tests["sentences"]]
predictor = load_predictor()

num_correct = 0
for (text, expected) in test_sents:
    pairs = test_pipeline(text, predictor)['subjects_with_verbs']
    num_correct += evaluate_subjects_with_verbs(pairs, expected)
    print("\n\n")

print("TEST ACCURACY: ", num_correct/len(test_sents))
