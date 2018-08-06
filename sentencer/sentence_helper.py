#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests, zipfile, io
import spacy

def get_sentences(link):
    r = requests.get(link)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    for fname in z.namelist():
        text = str(z.open(fname).read())
        return get_sents_from_text(text)

def get_sents_from_text(text):
    nlp = spacy.load('en_core_web_sm')
    doc = nlp(text)
    return list(doc.sents)
