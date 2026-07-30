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

# words() used to be a byte-identical copy of retro.words(), duplicated here
# because no shared core/ module existed yet when this file was split out.
# core.scripts.textutil is that shared home now, so this imports it instead
# of carrying its own copy (and its own STOP set) forward.
from core.scripts.textutil import words

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
