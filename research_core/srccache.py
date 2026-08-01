#!/usr/bin/env python3
"""Read-only access to the cached source text used for verbatim quote checks.

Extracted from retro.py: `load_manifest`, `source_text`, `src_sentences` and
`verify_quote` read files under the source-text cache (see
research_core.paths.CACHE) -- they know nothing about wikitext or the wiki
templates that reference a source, so they belong in research_core/ next to
research_core.textutil, which they use for sentence splitting and
quote normalisation.
"""
import os
import json
import re

from research_core.paths import CACHE
from research_core.profile import DEFAULT
from research_core.textutil import split_sentences, norm, slug


def load_manifest():
    return json.load(open(os.path.join(CACHE, "manifest.json")))


def source_text(title):
    p = os.path.join(CACHE, slug(title) + ".txt")
    return open(p).read() if os.path.isfile(p) else ""


def src_sentences(title, profile=DEFAULT, maxlen=420):
    body = source_text(title)
    if len(body) < 400:
        return []
    body = re.sub(r"\s+", " ", body)
    out = []
    for a, b in split_sentences(body):
        s = body[a:b].strip()
        if not (30 < len(s) < maxlen):
            continue
        if profile.junk.search(s):
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
