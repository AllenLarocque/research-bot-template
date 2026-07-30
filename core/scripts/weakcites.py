#!/usr/bin/env python3
"""Flag citations whose quote looks unlikely to support its sentence.

Heuristic: content-word overlap between the sentence and the quote, plus whether
they share an anchor (year / number / proper noun). Low overlap AND no shared
anchor => suspicious, worth putting in front of a human. This cannot decide
support; it just ranks the least-defensible pairs.

Callers are responsible for turning source markup into plain prose and a plain
quote string before calling these functions -- this module knows nothing about
where the sentence or quote text came from.
"""
import re
import unicodedata

STOP = set("""a an the and or but of in on at to for from by with as is was were be been being
it its this that these those which who whom whose has have had will would can could may might
not no than then there their they them he she his her him we our us you your i also more most
other such into over under between during after before while""".split())

# Read from sys.argv at module scope in the original script, which made the
# module impossible to import from a test. Now a plain default: callers that
# want a different threshold pass it as a parameter.
DEFAULT_THRESH = 0.20


def anchors(s):
    out = set(re.findall(r"\b(?:1[6-9]\d{2}|20\d{2})\b", s))
    out |= set(re.findall(r"\b\d[\d,.]{2,}\b", s))
    for m in re.finditer(r"\b([A-Z][a-zA-Z&.\-']+(?: [A-Z][a-zA-Z&.\-']+)+)", s):
        out.add(m.group(1).lower())
    return out


def words(s):
    """Content words: lowercased, stopwords and length-<=2 tokens dropped."""
    s = unicodedata.normalize("NFKD", s)
    for a, b in (("’", "'"), ("“", '"'), ("”", '"'), ("—", " "), ("–", " ")):
        s = s.replace(a, b)
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 2]


def overlap(sentence, quote):
    """Fraction of the sentence's content words also present in the quote.

    Extracted from the original weakcites.py:main, which computed this inline as
    `len(sw & qw) / max(len(sw), 1)` where sw/qw were sets of retro.words(...).
    """
    sw = set(words(sentence))
    qw = set(words(quote))
    return len(sw & qw) / max(len(sw), 1)


def is_weak(sentence, quote, thresh=DEFAULT_THRESH):
    """True if overlap is below `thresh` AND the pair shares no anchor.

    Mirrors the original inline condition `ov < THRESH and not shared`.
    """
    if overlap(sentence, quote) >= thresh:
        return False
    return not (anchors(sentence) & anchors(quote))
