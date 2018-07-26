from sva_utils import drop_modifiers, remove_prepositional_phrases
from sva_utils import substitute_infinitives_as_subjects
from sva_utils import simplify_compound_subjects, remove_adverbial_clauses
from preprocess_utils import remove_double_commas, remove_leading_noise
import textacy

def preprocess_sent(sentence_str):
    sentence_str = textacy.preprocess.normalize_whitespace(sentence_str)
    sentence_str = textacy.preprocess.unpack_contractions(sentence_str)
    # sentence_str = drop_modifiers(sentence_str)
    # sentence_str = remove_double_commas(sentence_str)
    # sentence_str = remove_leading_noise(sentence_str)
    # sentence_str = substitute_infinitives_as_subjects(sentence_str)
    # sentence_str = remove_prepositional_phrases(sentence_str)
    # sentence_str = remove_double_commas(sentence_str)
    # sentence_str = textacy.preprocess.normalize_whitespace(sentence_str)
    # sentence_str = simplify_compound_subjects(sentence_str)
    # sentence_str = remove_double_commas(sentence_str)
    # sentence_str = textacy.preprocess.normalize_whitespace(sentence_str)
    # sentence_str = sentence_str[0].upper() + sentence_str[1:]
    return sentence_str
