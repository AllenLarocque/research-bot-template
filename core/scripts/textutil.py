#!/usr/bin/env python3
"""Generic text utilities extracted from retro.py.

`split_sentences`, `words`, `norm` and `slug` all lived in retro.py alongside
`narrative_span` / `page_sentences` / `sources_used`, which parse
"Relationship"/"Entity footer" template wikitext. None of the four functions
here know what a wiki template, link or citation tag looks like -- they
operate on plain strings (prose, a query term, a page title) -- so they move
to core/ unchanged.

`plain()` (wikitext -> readable text) also lived in retro.py and the Task 8
brief's interface sketch listed it here too, but its own implementation
recognises link, ref-tag and template SYNTAX -- exactly the wikitext-structure
knowledge core/ must not have (see tests/test_layering.py, which scans core/
source text for that syntax literally, not just for behaviour). It moved to
adapters/mediawiki/retro.py instead, alongside the other wikitext-structure
functions. This is a deliberate deviation from the brief for that one
function; everything else here matches the brief's core.scripts.textutil
interface.

`words()` here is the single source of truth for "content words: lowercased,
stopwords and length-<=2 tokens dropped". core.scripts.weakcites used to carry
a byte-identical copy (there was no core/ home for it to import from yet); it
now imports this one instead.
"""
import re
import unicodedata

from core.scripts.profile import DEFAULT

STOP = set("""a an the and or but of in on at to for from by with as is was were be been being
it its this that these those which who whom whose has have had will would can could may might
not no than then there their they them he she his her him we our us you your i also more most
other such into over under between during after before while""".split())


def slug(t):
    return re.sub(r"[^A-Za-z0-9]+", "_", t)[:120]


def split_sentences(text, profile=DEFAULT):
    """Split prose into sentences, respecting known abbreviations. Returns
    list of (start, end) offsets relative to `text`."""
    spans, pos = [], 0
    for m in re.finditer(r"[.!?](?=[\s\"')\]]|$)", text):
        i = m.end()
        tail = text[max(0, i - 6):i]
        if any(tail.endswith(a) for a in profile.abbreviations):
            continue
        # skip decimals / initials like "J. H."
        if re.search(r"\b[A-Z]\.$", text[max(0, i - 3):i]):
            continue
        seg = text[pos:i]
        if len(seg.strip()) > 20:
            spans.append((pos, i))
            pos = i
    if len(text[pos:].strip()) > 20:
        spans.append((pos, len(text)))
    return spans


def words(s):
    s = unicodedata.normalize("NFKD", s)
    for a, b in (("’", "'"), ("“", '"'), ("”", '"'), ("—", " "), ("–", " ")):
        s = s.replace(a, b)
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 2]


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("—", "-"), ("–", "-"), ("−", "-"), (" ", " ")):
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()
