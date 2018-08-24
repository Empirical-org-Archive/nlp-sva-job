from allennlp.predictors import Predictor
from subject_verb_extraction import get_subject_verb_pairs
import subjects_with_verbs_to_reductions

def load_predictor(path="/var/lib/allennlp/elmo-constituency-parser-2018.03.14.tar.gz"):
    """
    Loads and returns local copy of AllenNLP model
    """
    print("Loading AllenNLP predictor...")
    predictor = Predictor.from_path(path)
    print("AllenNLP predictor loaded.")
    return predictor


def get_reduction(sent, predictor):
    """
    Takes a sentence and AllenNLP predictor, returns list of sentence reductions
    """
    subject_verb_pairs = get_subject_verb_pairs(sent, predictor)
    return [subjects_with_verbs_to_reductions.get_reduction(pair, sent) for pair in subject_verb_pairs]
