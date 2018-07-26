from allennlp.service.predictors import Predictor
from nltk.tree import Tree
from preprocess import preprocess_sent
from pattern.en import mood, tenses, lemma
from hashlib import sha256
import top100

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
    """    Currently returns list of tuples with (VP, NP) as each tuple
    Note that, consistent with reduction format, the verb comes first, then subject

    Will soon return pairs in the format:
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

    words = []
    if subject is None or len(subject) == 0: # No subject
        return words
    elif len(subject) == 1 and subject[0].label() in pronoun_tags: # Pronoun
        words.append({ 'word': subject[0][0], 'label': subject[0].label() })
    else:
        # Otherwise, identify the last noun tag and submit that (brittle heuristic)
        last_tag = None
        for i in range(0, len(subject)):
            child = subject[i]
            if child.label() == "NP": # Recursively identify sub-phrases
                return subject_words_from_phrase(child)
            last_tag = {'word': child[0], 'label': child.label()} if child.label() in singular_tags else last_tag
            last_tag = {'word': child[0], 'label': child.label()} if child.label() in plural_tags else last_tag
        if last_tag is not None:
            words.append(last_tag)
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

    print(get_verb_subject_pairs(tree))
    # mood = determine_sentence_mood(sent)
    # reductions = generate_reductions(pairs, mood)
    # print(reductions)
    print("\n\n")

# MARK: Test Script

predictor = load_predictor()
for sent in test_sents:
    print(sentence_to_pairs(sent, predictor))
