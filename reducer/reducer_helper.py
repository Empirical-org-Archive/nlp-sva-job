from allennlp.service.predictors import Predictor
from nltk.tree import Tree
from preprocess import preprocess_sent
from pattern.en import mood, tenses, lemma
from hashlib import sha256
import top100
import json

import subjects_with_verbs_to_reductions


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

    # Fragments (parsed same as declarative clause):
    for s in tree.subtrees(lambda t: t.label() == 'FRAG'):
        pairs += verb_subject_for_declarative_clause(s)

    for s in tree.subtrees(lambda t: t.label() == 'SINV'):
        pairs += verb_subject_for_subject_inversion(s)

    return { 'subjects_with_verbs': pairs }

# MARK: Extracting pairs from various clauses:

def verb_subject_for_declarative_clause(tree):
    """ Takes in the tree for a vanilla declarative clause (S tag)
        Returns list of subject, verb pairs, empty if none

        Broadly, covers cases:
        (1) Standard noun-phrase and verb-phrase as siblings: "Joyce is amazing"
        (2) Multiple verb phrases: "At once I was in heaven and danced freely on the sand"
        (3) Declarative clause verb-phrase as subject: "Swinging from vines is fun"

    """
    np, s_child = None, None # Possible subjects
    vps = []
    for i in range(0, len(tree)):
        child = tree[i]
        np = child if child.label() == "NP" else np
        s_child = child if child.label() == "S" else s_child
        vps += [child] if child.label() == "VP" else []

    vps = sum([unpack_verb_phrases(vp) for vp in vps], [])
    if np is not None: # Noun phrase as subject
        return [{ 'vp': vp, 'np': np } for vp in vps]
    elif s_child is not None: # Declarative clause as subject
        return [{ 'vp': vp, 'np': s_child } for vp in vps]
    # TODO: Under what circumstances should we return a pair with None np?
    return []


def verb_subject_for_sbarq(tree):
    """
    Takes tree for a SBARQ clause: question introduced by a wh-word or a wh-phrase
    Returns list of subject, verb pairs, empty if none

    Subject is typically implied by the SQ after the question word.
    The subject of "Who is John" is "John", which is contained in the SQ
    """
    wh_words = ["WHADJP", "WHAVP", "WHNP", "WHPP"]
    # Identify the SQ (main clause of wh-question) which contains verb and subject
    # Restrict to those SQs which immediately follow wh words
    for i in range(0, len(tree) - 1):
        wh = tree[i]
        sq = tree[i + 1]
        if wh.label() in wh_words and sq.label() == 'SQ':
            nps = [child for child in sq if child.label() == 'NP']
            return [{ 'vp': sq, 'np': np} for np in nps]
    return []

def verb_subject_for_subject_inversion(tree):
    """
    Takes tree for a SINV clause: clause with subject-auxillary inversion
    Example: "Never had I seen such a place"
    Returns list of subject, verb pairs, empty if none
    """
    verb_labels = ["MD", "VB", "VBZ", "VBP", "VBD", "VBN", "VBG"]

    # Find the subject, looking forwards
    for i in range(0, len(tree)):
        if tree[i].label() == 'NP':
            # Find the verb, looking backwards
            for j in reversed(range(0, i)):
                if tree[j].label() == 'VP':
                    return [{ 'np': tree[i], 'vp': tree[j] }]
                if tree[j].label() in verb_labels:
                    vp = Tree('VP', [tree[j]])
                    return [{ 'np': tree[i], 'vp': vp}]
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
    adj_tags = ["JJ", "JJR", "JJS"]
    noun_tags = pronoun_tags + singular_tags + plural_tags + wh_tags

    noun_words = []
    if subject is None: # No subject
        return noun_words
    elif subject.label() == "S":
        # Declarative clause as subject: "Swinging from vines is fun". Extract verb phrases as subject.
        return verb_words_from_phrase(subject)
    else:
        # Standard noun phrase. Gather noun words from the phrase.
        # If no noun phrases are present, subject may be adjective: "Melancholy hung over James"
        adj_words = []
        for i in range(0, len(subject)):
            child = subject[i]
            if child.label() == "NP": # Recursively identify sub-phrases
                noun_words += subject_words_from_phrase(child)
            elif child.label() in noun_tags:
                noun_words.append({'word': child[0], 'label': child.label()})
            elif child.label() in adj_tags:
                adj_words.append({'word': child[0], 'label': child.label()})
        return noun_words if noun_words else adj_words
    return []

# MARK: Verbs


def verb_words_from_phrase(vp):
    """
    Given a verb phrase, returns a list of the verb words in the phrase

    Broadly, handles cases:
    (1) Typical verbs
    (2) "to" before verbs without nesting. Usually in subjects: "To dance is to be free."
    """
    verb_tags = ["MD", "VB", "VBZ", "VBP", "VBD", "VBN", "VBG"]
    to_labels = ["TO"]

    if vp is None:
        return []

    words = []
    for i in range(0, len(vp)):
        child = vp[i]
        if child.label() in verb_tags + to_labels:
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

def get_reduction(sent, predictor):
    svpair_info = sentence_to_pairs(sent, predictor)
    return subjects_with_verbs_to_reductions.get_reduction(svpair_info['subjects_with_verbs'], svpair_info['text'])

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

if __name__ == '__main__':
    # Test our subject-verb accuracy
    with open('../test/data/sentences.json') as test_file:
        tests = json.load(test_file)

    test_sents = [(example["text"], example["subjects_with_verbs"]) for example in tests["sentences"]]
    predictor = load_predictor()

    for (text, expected) in test_sents:
        print("Reduction: ", get_reduction(text, predictor))
        print("Actual: ", expected)
        print("\n\n")

    # num_correct = 0
    # for (text, expected) in test_sents:
    #     pairs = test_pipeline(text, predictor)['subjects_with_verbs']
    #     num_correct += evaluate_subjects_with_verbs(pairs, expected)
    #     print("\n\n")
    #
    # print("TEST ACCURACY: ", num_correct/len(test_sents))
