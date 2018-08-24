# nlp-sva-job
An nlp job aimed at producing a model that can detect subject verb agreement errors in sentences.

We train our model by pulling millions of sentences in training data (`sentencer`),
reducing those sentences into reductions of their subject-verb pairs (`reducer`),
and storing those reductions into a database.

To evaluate sentences using this model, we run the classifier code located
in our [Quill-NLP-Tools-and-Datasets](https://github.com/empirical-org/Quill-NLP-Tools-and-Datasets)
under `utils`.

## Sentencer

The sentencer pulls down links to books in Project Gutenberg and adds sentences from those books into our database table. We train our model on these sentences.

## Reducer

The reducer takes in our database's sentences and stores "reductions" of each sentence, with information about the mood of the sentence, and the subject and verb for each subject-verb pair.

To run the reducer, you'll have to download the AllenNLP Constituency Parsing model, which can be found under Constituency Parsing at: https://allennlp.org/models. We recommend placing this model into the file path `/var/lib/allennlp/elmo-constituency-parser-2018.03.14.tar.gz`. Alternatively, if you store your model elsewhere, simply change the path location for the `load_predictor` method in `reducer/reducer_helper.py`.
