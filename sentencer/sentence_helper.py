#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests, zipfile, io
import spacy
import json
nlp = spacy.load('en_core_web_sm')

CHUNK_SIZE = 1000

def get_sentences(link):
    link = json.loads(link) # unquoute the quoted string
    r = requests.get(link)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    for fname in z.namelist():
        text = str(z.open(fname).read())
        return get_sents_from_text(text)

def get_sents_from_text(text):
    # we use spacy to extract sentences from the whole book at once (memory
    # problem) instead, break the text into chunks.
    sents = [] 
    text_left = len(text)
    start_index=0
    leftovers = ''
    while CHUNK_SIZE < text_left: 
        # create text chunk
        chunk = leftovers + text[start_index:start_index+CHUNK_SIZE]
        # collect sentences
        doc = nlp(chunk)
        sents += list(doc.sents)[:-1]
        # store leftovers
        leftovers = chunk[list(doc.sents)[-1].start_char:]
        start_index += CHUNK_SIZE
        text_left -= CHUNK_SIZE
    # last chunk may not be even chunk.
    chunk = leftovers + text[start_index:-1]
    # collect sentences
    doc = nlp(chunk)
    sents += list(doc.sents)
    return [str(s) for s in sents]
