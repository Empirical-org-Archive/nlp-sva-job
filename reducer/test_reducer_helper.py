from reducer_helper import get_reduction, load_predictor
from subject_verb_extraction import (get_subject_verb_pairs, test_pipeline,
    subject_verb_pairs_are_equal)
import time
import json
from collections import Counter

def test_get_reduction():
    """
    Tests our reduction accuracy for get_reduction in reducer_helper
    Prints accuracy
    """
    predictor = load_predictor()
    with open('../test/data/sentences.json') as f:
        test_dict = json.load(f)

    incorrect_sentences = 0
    total_sentences = 0
    start_time = time.time()
    for sentence_obj in test_dict['sentences']:
        total_sentences += 1
        sent = sentence_obj["text"]
        expected_reductions = Counter(sentence_obj['reductions']) # order doesn't matter
        subjects_with_verbs = sentence_obj['subjects_with_verbs']
        actual_reductions = get_reduction(sent, predictor)
        actual_reductions = Counter(actual_reductions)
        if expected_reductions != actual_reductions:
            incorrect_sentences += 1
    end_time = time.time()

    print('Time to test: {}'.format(end_time - start_time))
    print('Out of {} sentences,'.format(total_sentences))
    print('There were {} incorrect sentences.'.format(incorrect_sentences))
    accuracy = 100 * (total_sentences - incorrect_sentences) / total_sentences
    print('{} percent correct.'.format(accuracy))
    return accuracy

def test_get_subject_verb_pairs():
    """
    Tests how accurate we are at extracting subject-verb pairs from sentences
    Writes verbose output for each pair
    """
    predictor = load_predictor()
    with open('../test/data/sentences.json') as f:
        test_dict = json.load(f)
    print("Model loaded, testing beginning")

    num_correct = 0
    for example in test_dict["sentences"]:
        pairs = test_pipeline(example["text"], predictor)
        if subject_verb_pairs_are_equal(pairs, example["subjects_with_verbs"]):
            num_correct += 1
        print("\n\n")

    num_sentences = len(test_dict["sentences"])
    print("TEST ACCURACY: {}".format(num_correct/num_sentences))

if __name__ == '__main__':
    # accuracy = test_get_reduction()
    # assert accuracy == 72.41379310344827 # Refactor began at this accuracy
    test_get_subject_verb_pairs()
