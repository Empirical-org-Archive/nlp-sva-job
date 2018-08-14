#TODO: Move this file to another folder
from pattern.en import conjugate,tenses
import itertools
import textacy

def permute_sentence(s, alt_verbs):
    '''
    s = "The boy {} good and the girl {} bad."
    alt_verbs = [ ['are', 'is'], ['are', 'is'] ]

    returns ["The boy is good and the girl is bad.",
             "The boy are good and the girl are bad.",
             "The boy is good and the girl are bad.",
             "The boy are good and the girl is bad."]
    '''
    result = [s.format(*perm) for perm in itertools.product(*alt_verbs)]
    return result

def get_possible_forms(verb):
    """Given a verb return alternative forms of the verb that
    have the same tense, but a different person, number, or both.
    
    ie, verb="is", return ["is", "are", "am"]
    """
    tense, aspect = get_tense_and_aspect(verb)
    results = []
    for number in ["singular", "plural"]:
        for person in [1,2,3]:
            results.append(conjugate(verb, tense=tense, aspect=aspect,
                number=number, person=person))
    return list(set(results))

def get_alt_sentences(sent):
    '''Given a sentence, remove the verbs and replace with {}.
    return the ghost verb sentence and a list of verb alternative lists

    ie, "John is smart but Theresa is a genius."

    would return,
    ["John {} smart but Theresa {} a genius.", [['is', 'are', 'am'],
    ['is','are','am']]]
    '''
    d = textacy.Doc(sent, lang='en_core_web_sm')
    # create ghost sentence and initial verb list
    ghost_sentence = ''
    initial_verbs = []
    end_idx_of_last_verb = 0
    for t in d:
        if t.tag_.startswith('VB'):
            ghost_sentence += sent[end_idx_of_last_verb:t.idx] + '{}'
            end_idx_of_last_verb = t.idx+len(t.text)
            initial_verbs.append(t.text)
    ghost_sentence += sent[end_idx_of_last_verb:]

    alt_verbs = [get_possible_forms(v) for v in initial_verbs]
    return permute_sentence(ghost_sentence, alt_verbs)


def get_tense_and_aspect(verb):
    t = tenses(verb)
    for tx in t:
        if tx[0] and tx[4]:
            return (tx[0], tx[4])
    return (None, None)
