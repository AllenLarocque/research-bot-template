#!/usr/bin/env python3
"""Detect a date asserted about an entity in running prose that disagrees with
that entity's own structured founding/closing dates.

A wiki can be internally inconsistent while every page passes every citation
check: page A says a mill closed in 2008, page B's own record says 2010, and
both are separately "verified".

The check is deliberately narrow: for a subject with known founding/closing
years, look at every place its name is mentioned in some other page's prose,
and inspect a short window after the name for a year and an event word
(founded, opened, built, closed, shut). Flag when the year disagrees with the
subject's own recorded value.

This cannot decide who is right. It says two pages disagree, which is always
worth a look.

Two suppression rules keep this useful instead of pure noise:

  * a noun for a thing the subject OWNS, standing between the name and the
    year, means the date belongs to that thing, not to the subject itself
    ("Acme's depot ... closed in 1983"). What counts as an "owned thing" is
    domain vocabulary, not something this module knows -- callers pass it in
    via a `Profile`'s `owned_things`;
  * a pronoun between the name and the year means the sentence has moved on
    to a different subject ("opened it in 1912", "It was formed in 2008").
"""
import re

from core.scripts.profile import DEFAULT

OPEN_FIELDS = ("founded_date", "commissioned_date", "granted_date")
CLOSE_FIELDS = ("closed_date", "dissolved_date")
OPEN_WORDS = r"founded|established|opened|built|incorporated|commissioned|formed"
CLOSE_WORDS = r"closed|closure|shut|dissolved|demolished|dismantled"

_YEAR = r"\b(1[6-9]\d{2}|20\d{2})\b"
_PRONOUNS = r"\b(it|its|which|that|they|whose|this)\b"


def date_conflicts(subject, prose, years, profile=DEFAULT, window=90):
    """Mentions of `subject` in `prose` whose nearby year disagrees with `years`.

    `years` is `subject`'s own {field: year} (e.g. {"closed_date": "1990"}).
    `profile.owned_things` is a regex for nouns that suppress a match when
    they stand between the name and the year (see module docstring) -- an
    injected parameter, not a constant, because it is domain vocabulary.
    Defaults to `DEFAULT`, whose `owned_things` matches nothing.

    Extracted from the original script's `main`, which searched every
    occurrence of `subject` in a host page's prose, inspected a `window`-char
    segment after each occurrence, and stopped at the first year in that
    segment for which an open/close event word could be found -- whether or
    not that year actually conflicted. That "stop after the first candidate
    year" behaviour is preserved here: at most one conflict is reported per
    occurrence of `subject`.

    Returns a list of dicts, one per flagged occurrence:
    {"kind": "open"|"close", "year": "1983", "own": ["1990"], "context": "..."}
    """
    conflicts = []
    if not years:
        return conflicts
    for m in re.finditer(re.escape(subject), prose):
        seg = prose[m.end():m.end() + window]
        for yr in re.findall(_YEAR, seg):
            before = seg[:seg.find(yr)]
            after = seg[seg.find(yr) + 4: seg.find(yr) + 34]
            if profile.owned_things.search(before) or \
               profile.owned_things.search(after):
                continue
            if re.search(_PRONOUNS, before, re.I):
                continue
            kind = None
            if re.search(OPEN_WORDS, before, re.I):
                kind = "open"
            elif re.search(CLOSE_WORDS, before, re.I):
                kind = "close"
            if not kind:
                continue
            fields = OPEN_FIELDS if kind == "open" else CLOSE_FIELDS
            own = [years[f] for f in fields if f in years]
            if own and yr not in own:
                conflicts.append({
                    "kind": kind,
                    "year": yr,
                    "own": own,
                    "context": seg[:120].strip(),
                })
            break
    return conflicts
