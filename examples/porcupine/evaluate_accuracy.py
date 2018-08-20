import sys
import time
from sva_classifier import get_feedback as get_sva_feedback
# get_feedback currently returns None if no error, otherwise human-readable feedback

"""
This evaluation program takes a file of annotations and returns metrics about
how well our model performs on detecting errors within those annotations.
"""

def get_test_data(annotated_file):
    """
    Reads test data into a list of dictionaries. Each dictionary in the form:
    {
    "original": "Genetic testing are evil.",
    "sva_error": True,
    "correct": "Genetic testing is evil."
    }

    We will currently store only one correct modification, though there may be
    multiple acceptable correct modifications.

    Currently, we are reading from a m2 file in the style of the NUCLE .m2 files
    These contain each sentence followed by their annotations
    """
    LENGTH_CUTOFF = 500 #Toss out any sentences that are ridiculously long
    examples = []
    cur_sentence = None
    cur_annotations = []
    with open(annotated_file, "r") as file:
        for line in file.read().splitlines():
            if len(line) == 0:
                continue
            elif line[0] == 'S':
                if cur_sentence and len(cur_sentence) < LENGTH_CUTOFF:
                    example = training_example_from_annotations(cur_sentence, cur_annotations)
                    if example["sva_error"]: # Currently only positive sampling
                        examples.append(example)
                cur_sentence = line[2:]
                cur_annotations = []
            elif line[0] == 'A':
                annotation = parse_annotation(line)
                cur_annotations.append(annotation)
    return examples

def parse_annotation(annotation_line):
    """
    Given annotation line in form
    A 22 23|||Wform|||combining|||REQUIRED|||-NONE-|||0

    Returns annotation dictionary with relevant information
    Note: the last number denotes the grader's ID. We only add sentences if
    both graders agree on a given annotation.
    """
    words = annotation_line.split("|||")
    annotation = {}
    annotation["error_type"] = words[1]
    annotation["start_index"] = int(words[0].split()[1])
    annotation["end_index"] = int(words[0].split()[2])
    annotation["correct_words"] = words[2]
    return annotation

def training_example_from_annotations(sent, annotations):
    """
    Given a sentence and list of annotations, returns a training example

    Generates the correct sentence by implementing all SVA annotation changes
    """
    example = {"original": sent}
    annotations = [a for a in annotations if a["error_type"] == "SVA"]
    # Only add annotations if at least two graders agree on the annotation:
    annotations = [a for a in annotations if annotations.count(a) > 1]
    example["sva_error"] = len(annotations) > 0
    for ann in annotations:
        sent = correct_sentence_from_annotation(sent, ann)
    example["correct"] = sent
    return example

def correct_sentence_from_annotation(sent, annotation):
    """
    Given a sentence, and annotation dictionary as described above
    Reconstructs the correct sentence and returns that sentence
    """
    words = sent.split()
    words[annotation["start_index"]:annotation["end_index"]] = annotation["correct_words"].split()
    return " ".join(words)
    return example

def get_dummy_test_data():
    """
    Returns three dummy test sentences for debugging use.
    """
    return [
        {
            "original": "Hence , the social media sites serves as a platform for the connection .",
            "sva_error": True,
            "correct": "Hence , the social media sites serve as a platform for the connection ."
        },
        {
            "original": "Howard Garner studied the effect of multiple intelligences amongst people and stated that interpersonal intelligence is a form of skills on its own - some has it , some does not .",
            "sva_error": True,
            "correct": "Howard Garner studied the effect of multiple intelligences amongst people and stated that interpersonal intelligence is a form of skills on its own - some have it , some do not ."
        },
        {
            "original": "Sometimes, sentences are correct.",
            "sva_error": False,
            "correct": "Sometimes, sentences are correct."
        }
    ]

def evaluate_example(example, strict=False, verbose=True, log_sock=sys.stdout):
    """
    Takes in one example in the dictionary format described above:
    { "original": ---, "sva_error": ---,  "correct": ---}

    If not strict: returns True if our classifier correctly tags the sentence
    as sva_error or not sva_error. False otherwise.

    TODO: If strict: the correct sentence generated by our model must match the correct
    sentence stored in the training example

    If verbose, will print out logs as we evaluate sentences
    """
    feedback = get_sva_feedback(example["original"])
    sva_error_found = True if feedback else False
    matches = (sva_error_found == example["sva_error"])
    if verbose:
        log_sock.write("Original: {}\n".format(example["original"]))
        log_sock.write("SVA Error: {}\n".format(example["sva_error"]))
        log_sock.write("Correct: {}\n".format(example["correct"]))
        if matches:
            log_sock.write("MATCH $$$$$$$$$$$$$$$$$$$$$$$$$$$$$\n")
        else:
            log_sock.write("MISMATCH !!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        if feedback:
            log_sock.write(feedback + "\n")
        else:
            log_sock.write("No SVA error found.\n")
        log_sock.write("-----------------------------------------------------\n\n")
    return matches


def evaluate_examples(examples, strict=False, verbose=True, log_sock=sys.stdout):
    """
    Evaluates many examples, returns accuracy metrics on those examples.
    Strict and verbose params are identical to evaluate_example
    """
    num_examples = len(examples)
    num_matched = 0
    report_frequency = 3

    for i, ex in enumerate(examples):
        if evaluate_example(ex, strict=strict, verbose=verbose, log_sock=log_sock):
            num_matched += 1
        if i % report_frequency == 0:
            print("Evaluated {} examples, {} % complete. ".format(i, 100*i/num_examples))

    accuracy = num_matched/num_examples
    if verbose:
        print("Accuracy: {}".format(accuracy))
        log_sock.write("Accuracy: {}\n".format(accuracy))
    return accuracy


if __name__ == '__main__':
    ANNOTATED_FILE = "../../test/data/nucle-test-official-2014.combined.m2"
    LOG_FILE = "../../test/logs/nucle-test-data-logs.txt"
    start_time = time.time()

    print("Reading test data")
    test_data = get_test_data(ANNOTATED_FILE)
    test_data = test_data[:3]
    print("Number of test examples: ", len(test_data))
    print("Test data head: ", test_data[:3])
    print("Evaluating examples. Logging output to ", LOG_FILE)
    with open(LOG_FILE, 'w') as log_sock:
        accuracy = evaluate_examples(test_data, strict=False, verbose=True, log_sock=log_sock)
        log_sock.seek(0, 0) #be kind, rewind
        log_sock.write("Accuracy: {}\n".format(accuracy))
        end_time = time.time()
        log_sock.write("Evaluation Time: {0:.2f} seconds\n\n".format(end_time - start_time))
