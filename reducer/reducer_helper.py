from allennlp.service.predictors import Predictor
from subject_verb_extraction import get_subject_verb_pairs
import subjects_with_verbs_to_reductions

def load_predictor(path="/var/lib/allennlp/elmo-constituency-parser-2018.03.14.tar.gz"):
    """Load local copy of AllenNLP model"""
    return Predictor.from_path(path)


def get_reduction(sent, predictor):
    """
    High-level function to take a sentence and AllenNLP predictor,
    returns list of reductions of sentence.

    Imported and used in several other modules
    """
    subject_verb_pairs = get_subject_verb_pairs(sent, predictor)
    return [subjects_with_verbs_to_reductions.get_reduction(pair, sent) for pair in subject_verb_pairs]
