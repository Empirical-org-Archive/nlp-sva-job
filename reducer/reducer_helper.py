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
    words = {'sentence': []}
    for pair in pairs['sentence']:
        np = pair['np']
        vp = pair['vp']
        words['sentence'].append({'vp': verb_words_from_phrase(vp), 'np': subject_words_from_phrase(np)})
    return words


def get_verb_subject_phrases(tree):
    """
    Returns pairs in the format:
    { 'sentence': [{'vp': Tree(Verb phrase), 'np': Tree(Noun phrase)}, {'vp': Tree(second verb phrase), 'np': Tree(second noun phrase)}, ...] }
    """
    pairs = []
    for s in tree.subtrees(lambda t: t.label() == 'S'):
        # This is an S subtree, so we extract VP, maybe NP here
        np, vp = None, None
        for i in range(0, len(s)):
            child = s[i]
            np = child if child.label() == "NP" else np
            vp = child if child.label() == "VP" else vp
        pairs.append({ 'vp': vp, 'np': np })

    for s in tree.subtrees(lambda t: t.label() == 'SBARQ'):
        # "Direct question introduced by a wh-word or a wh-phrase"
        np, vp = None, None
        wh_words = ["WHADJP", "WHAVP", "WHNP", "WHPP"]
        for i in range(0, len(s) - 1):
            # Identify the wh-word and the possible subsequent SQ
            phrase = s[i]
            next_phrase = s[i + 1]
            if phrase.label() in wh_words and next_phrase.label() == 'SQ':
                pairs.append({ 'vp': next_phrase, 'np': phrase})

    return { 'sentence': pairs }


def print_verb_subject_phrases(pairs):
    """Print verb_subject pairs in readable form"""
    print("Verb Subject Pairs: ")
    for pair in pairs['sentence']:
        print("Noun Phrase: ", ' '.join(pair['np'].leaves()) if type(pair['np']) is Tree else "None")
        print("Verb Phrase: ", ' '.join(pair['vp'].leaves()) if type(pair['vp']) is Tree else "None")

# MARK: Moods

def determine_sentence_mood(sentence_str):
    """Returns mood of sentence string"""
    conditional_words = ["assuming", "if", "in case", "no matter how",
            "supposing", "unless"]
    result = mood(sentence_str)
    if result == 'imperative':
        return result # takes care of imperative
    for cw in conditional_words:
        if cw in sentence_str.lower():
            return 'possible_conditional'
    return 'indicative' # indicative

# MARK: Subjects

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
    if subject is None or len(subject) == 0: # No subject
        return words
    else:
        # Otherwise, identify the last noun tag and submit that (brittle heuristic)
        for i in reversed(range(0, len(subject))):
            child = subject[i]
            if child.label() == "NP": # Recursively identify sub-phrases
                return subject_words_from_phrase(child)
            if child.label() in noun_tags:
                return [{'word': child[0], 'label': child.label()}]
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


def verb_reduction(verb, tag):
    """Given string of existing verb, returns its corresponding reduction
    That's the verb itself if its lemma is in the top100, else its hash"""
    if lemma(verb.lower()) in top100.verbs:
        return verb.upper()
    else:
        h = sha256(str(tenses(verb)).encode('utf_8')).hexdigest()
        result = tag + '_' + h
        return result


def sentence_to_pairs(sent, predictor):
    """ Takes a sentence and AllenNLP predictor, returns the list of Reductions
    """
    processed = preprocess_sent(sent)
    parse = predictor.predict_json({"sentence": processed})
    tree = Tree.fromstring(parse["trees"])
    return {
        'subjects_with_verbs': get_verb_subject_pairs(tree),
        'sentence': sent
    }

def get_reduction(data, allennlp_predictor):
    sent = json.loads(data)['data']
    return sentence_to_keys(sent, allennlp_predictor)

# MARK: Test Sentences and Pipeline

test_sents = [
    "Project Gutenberg eBooks are often created from several printed editions, all of which are confirmed as Public Domain in the U.S. unless a copyright notice is included.",
    "Sometimes, I’ve believed as many as six impossible things before breakfast.",
    "It has been a terrible, horrible, no good, very bad day.",
    "The man, the boy, or the girls are frauds.",
    "Mr. and Mrs. Dursley of number four, Privet Drive, were proud to say that they were perfectly normal, thank you very much.",
    "The book, which is 1000 pages long, is an excellent read.",
    "The hippo lazily floated down the river.",
    "John Somerville occupied a suite of apartments in a handsome lodging-house on Walnut Street.",
    "People are tall.",
    "Don't go there."
]
test_tree_str = "(S (NP (NP (NNP Mr.) (CC and) (NNP Mrs.) (NNP Dursley)) (PP (PP (IN of) (NP (NN number) (CD four))) (, ,) (NP (NNP Privet) (NNP Drive)) (, ,))) (VP (VBD were) (ADJP (JJ proud) (S (VP (TO to) (VP (VB say) (SBAR (IN that) (S (NP (PRP they)) (VP (VP (VBD were) (ADJP (RB perfectly) (JJ normal))) (, ,) (S (VP (VBP thank) (NP (PRP you)) (ADVP (RB very) (RB much)))))))))))) (. .))"
test_tree = Tree.fromstring(test_tree_str)

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

    for pair in pairs['sentence']:
        subject = pair['np']
        print(subject_words_from_phrase(subject))
        vp = pair['vp']
        print(verb_words_from_phrase(vp))

    pairs = get_verb_subject_pairs(tree)
    print(pairs)
    return pairs

def evaluate_subjects_with_verbs(actual, expected):
    actual, expected = sorted(actual, key=lambda k: k["np"][0]["word"]), sorted(expected)
    if actual == expected:
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
    pairs = test_pipeline(text, predictor)
    num_correct += evaluate_subjects_with_verbs(pairs, expected)
    print("\n\n")

print("TEST ACCURACY: ", num_correct/len(test_sents))
