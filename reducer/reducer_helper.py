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
    """    Returns list of tuples with (VP, NP) as each tuple
    Note that, consistent with reduction format, the verb comes first, then subject
    """
    pairs = []
    for s in tree.subtrees(lambda t: t.label() == 'S'):
        # This is an S subtree, so we extract VP, maybe NP here
        np, vp = None, None
        for i in range(0, len(s)):
            child = s[i]
            np = child if child.label() == "NP" else np
            vp = child if child.label() == "VP" else vp
        pairs.append((vp, np))
    return pairs


def print_verb_subject_pairs(pairs):
    """Print verb_subject pairs in readable form"""
    print("Verb Subject Pairs: ")
    for pair in pairs:
        print("Noun Phrase: ", pair[1].leaves() if type(pair[1]) is Tree else "None")
        print("Verb Phrase: ", pair[0].leaves() if type(pair[0]) is Tree else "None")

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


def noun_string_from_subject(subject):
    """
    Given subject as noun_phrase tree, extracts relevant noun_string code
    Four cases - blank, pronoun, other (plural/singular), combination
    Currently doesn't handle combinations, but returns list of noun classifications
    """
    pronoun_tags = ["PRP", "PRP$", "WP", "WP$"]
    singular_tags = ["NN", "NNP"]
    plural_tags = ["NNS", "NNPS"]

    noun_strings = []
    if subject is None or len(subject) == 0: # No subject
        noun_strings.append("")
    elif len(subject) == 1 and subject[0].label() in pronoun_tags: # Pronoun
        noun_strings.append(subject[0][0].upper())
    else:
        # Otherwise, identify the last noun tag and submit that (brittle heuristic)
        last_tag = ""
        for i in range(0, len(subject)):
            child = subject[i]
            if child.label() == "NP": # Recursively identify sub-phrases
                return noun_string_from_subject(child)
            last_tag = "SG" if child.label() in singular_tags else last_tag
            last_tag = "PL" if child.label() in plural_tags else last_tag
        noun_strings.append(last_tag)
    return noun_strings

# MARK: Verbs


def verb_reductions_from_verb_phrase(vp):
    "Given a verb phrase, returns a list of the verb reductions"
    verb_tags = ["MD", "VB", "VBZ", "VBP", "VBD", "VBN", "VBG"]
    verb_reductions = []
    for i in range(0, len(vp)):
        child = vp[i]
        if child.label() in verb_tags:
            verb_reductions.append(verb_reduction(child[0], child.label()))
        if child.label() == "VP":
            verb_reductions += verb_reductions_from_verb_phrase(child)
    return verb_reductions


def verb_reduction(verb, tag):
    """Given string of existing verb, returns its corresponding reduction
    That's the verb itself if its lemma is in the top100, else its hash"""
    if lemma(verb.lower()) in top100.verbs:
        return verb.upper()
    else:
        h = sha256(str(tenses(verb)).encode('utf_8')).hexdigest()
        result = tag + '_' + h
        return result

# MARK: Generating Reductions

def generate_reductions(verb_subject_pairs, mood):
    """Given a list of verb_subject pairs and a mood, generates list of reductions
    [ (verb_phrase, subject_phrase), ...] =>
    => [INDICATIVE-VBDtenses(began):VBGtenses(crying)>SG,  ...]
    """
    reductions = []
    for vp, np in verb_subject_pairs:
        m = mood.upper() + '-'
        vs = ':'.join(verb_reductions_from_verb_phrase(vp))
        ns = '>' + ':'.join(noun_string_from_subject(np))
        tag = m + vs + ns
        reductions.append(tag)
    reductions = list(set(reductions)) #dedup reductions
    return reductions


def sentence_to_keys(sent, predictor):
    """ Takes a sentence and AllenNLP predictor, returns the list of Reductions
    """
    sent = preprocess_sent(sent)
    parse = predictor.predict_json({"sentence": sent})
    tree = Tree.fromstring(parse["trees"])
    pairs = get_verb_subject_pairs(tree)
    mood = determine_sentence_mood(sent)
    reductions = generate_reductions(pairs, mood)
    return reductions

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
    # sent = preprocess_sent(sent)
    print("Processed Sentence: ", sent)
    parse = predictor.predict_json({"sentence": sent})
    tree = Tree.fromstring(parse["trees"])
    print("Tree: \n", tree)
    pairs = get_verb_subject_pairs(tree)
    print_verb_subject_pairs(pairs)
    mood = determine_sentence_mood(sent)
    reductions = generate_reductions(pairs, mood)
    print(reductions)
    print("\n\n")

# MARK: Test Script

predictor = load_predictor()
for sent in test_sents:
    test_pipeline(sent, predictor)
