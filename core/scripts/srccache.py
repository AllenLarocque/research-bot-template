#!/usr/bin/env python3
"""Read-only access to the cached source text used for verbatim quote checks.

Extracted from retro.py: `load_manifest`, `source_text`, `src_sentences` and
`verify_quote` read files under the source-text cache (see
core.scripts.paths.CACHE) -- they know nothing about wikitext or the wiki
templates that reference a source, so they belong in core/ next to
core.scripts.textutil, which they use for sentence splitting and
quote normalisation.
"""
import os
import json
import re

from core.scripts.paths import CACHE
from core.scripts.textutil import split_sentences, norm, slug

# Reference-list / navigation debris that must never be offered as a quote.
_JUNK = re.compile(
    r"ISBN|ISSN|doi:|Retrieved \d|retrieved 20|Archived from|↑|\[ edit \]|"
    r"Wayback Machine|Cite \w+|www\.|http|@|Special Collections|"
    r"Oral History|\bp\. \d+|\bpp\. \d+|Harbour Publ|usw[.:]|"
    r"Privacy policy|Toggle the|Skip to|Search Search|Jump to|Main menu|"
    r"Sections News|Subscribe|Sign in|Log in|Newsletter|All rights reserved|"
    r"Table of contents|Read Edit|View history|Download as PDF|"
    r"About this capture|COLLECTED BY|\d+ captures|success fail|TIMESTAMPS", re.I)


def load_manifest():
    return json.load(open(os.path.join(CACHE, "manifest.json")))


def source_text(title):
    p = os.path.join(CACHE, slug(title) + ".txt")
    return open(p).read() if os.path.isfile(p) else ""


def src_sentences(title, maxlen=420):
    body = source_text(title)
    if len(body) < 400:
        return []
    body = re.sub(r"\s+", " ", body)
    out = []
    for a, b in split_sentences(body):
        s = body[a:b].strip()
        if not (30 < len(s) < maxlen):
            continue
        if _JUNK.search(s):
            continue
        # mostly citation apparatus: lots of bracketed refs or digits
        if len(re.findall(r"\[\s*\d+\s*\]", s)) > 1:
            continue
        letters = sum(c.isalpha() for c in s)
        if letters < 0.6 * len(s):
            continue
        out.append(s)
    return out


def verify_quote(quote, title):
    """Is `quote` verbatim in the cached text of `title`?"""
    body = norm(source_text(title))
    parts = [norm(p) for p in re.split(r"\.\.\.|…|\[\.\.\.\]", quote)]
    parts = [p for p in parts if len(p) >= 10]
    return bool(parts) and all(p in body for p in parts)
