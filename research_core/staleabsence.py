#!/usr/bin/env python3
"""Find claims that something is absent, so a caller can check they still hold.

A page that says "the Workers' Unity League has no page here" is making a claim
about a collection, not about its subject, and that kind of claim expires
silently. Nothing warns the sentence when the missing page is created. In the
2026-08 voice cleanup two of them had already gone false: Campbell River said a
1938 fire had no page while the page existed and was being edited in the same
pass, and Sayward said William P. Sayward had none on the day he was created.

Both were noticed only because an unrelated pattern happened to fire on the same
sentence. That is luck, and luck does not scale to a corpus.

This module locates the claims and names their subjects. It cannot know what
exists -- that is the caller's, and in a wiki it is an API call -- so `expired`
takes the set of things that do. Keeping the two apart is what makes this
testable without a network and portable to any collection that says "we do not
have X".

Nothing here knows what a wiki is. Wikilink targets are the most reliable
subject a wiki page can offer, and callers pass them in through `extra_names`.
"""
import re

from research_core.textutil import split_sentences
from research_core.profile import DEFAULT

# Claims of absence, in the forms the corpus actually used. "red link" is
# deliberately NOT one of them: a red link is a genuine invitation to a future
# contributor and turning blue is that invitation being accepted, not a defect.
# The defect is a SENTENCE asserting the absence, which stops being true.
ABSENCE = re.compile(
    r"\b(?:has|have)\s+no\s+pages?\s+here\b"
    r"|\bno\s+pages?\s+here\b"
    r"|\bno\s+page\s+for\b"
    r"|\bis\s+not\s+on\s+(?:this|the)\s+wiki\b",
    re.I)

# A run of capitalised words, which is what a page title looks like in prose.
# Lowercase joiners break the run, so "Gray, David Sturdy and Judge Arthur Lord"
# yields three names rather than one.
_NAME_RUN = re.compile(r"\b[A-Z][\w.'’\-]*(?:\s+[A-Z][\w.'’\-]*)*")

# Stripped from the front of a run: a sentence-initial article is capitalised
# like a name but is not part of the title.
_ARTICLE = re.compile(r"^(?:The|A|An)\s+", re.I)

# A run that is only one of these is sentence furniture, not a subject.
_FURNITURE = frozenset(
    "the a an it he she they this that these those there here and but or "
    "no not none nothing".split())


class Claim(object):
    """One assertion of absence, and the sentence carrying it."""

    def __init__(self, phrase, sentence, start, end):
        self.phrase = phrase
        self.sentence = sentence
        self.start = start
        self.end = end

    def __repr__(self):
        return "Claim(%r, %r)" % (self.phrase, self.sentence[:60])

    def __eq__(self, other):
        return (isinstance(other, Claim)
                and (self.phrase, self.start, self.end)
                == (other.phrase, other.start, other.end))

    def __hash__(self):
        return hash((self.phrase, self.start, self.end))


def absence_claims(text, profile=DEFAULT):
    """Every assertion of absence in `text`, with its containing sentence.

    Sentences come from research_core.textutil, so initials and abbreviations
    are respected -- "William P. Sayward" must not split at the initial, or the
    subject is severed from the claim about it.
    """
    spans = split_sentences(text, profile)
    out = []
    for m in ABSENCE.finditer(text):
        sentence = text
        for a, b in spans:
            if a <= m.start() < b:
                sentence = text[a:b].strip()
                break
        out.append(Claim(m.group(0), sentence, m.start(), m.end()))
    return out


def candidate_names(sentence):
    """Page titles a sentence might be asserting the absence of.

    Deliberately generous: a wrong candidate costs one existence lookup, while a
    missed one costs the whole point of the check. Both "The Workers' Unity
    League" and "Workers' Unity League" are offered, because the sentence
    capitalises the article and the title does not carry it.
    """
    out = []
    for m in _NAME_RUN.finditer(sentence):
        run = m.group(0).strip()
        if not run or run.lower() in _FURNITURE:
            continue
        if run not in out:
            out.append(run)
        bare = _ARTICLE.sub("", run).strip()
        if bare and bare != run and bare.lower() not in _FURNITURE and bare not in out:
            out.append(bare)
    return out


def expired(pages, present, extra_names=None, sentences=None, profile=DEFAULT):
    """[(title, Claim, [names that now exist])] for claims that have gone false.

    `present` is the set of titles that exist. `extra_names(title, sentence)`
    may supply subjects this module cannot see -- in a wiki, the sentence's
    link targets, which are a better answer than any capitalisation heuristic.

    `sentences(title, text)` cuts a page into regions before any of this runs.
    Markup is not prose: sentence punctuation does not bound a template
    parameter or a heading, so a "sentence" taken from raw markup can run
    across half a page and bury the claim's subject among everything else
    capitalised near it. Only a caller that understands the format knows where
    the regions are. Without it the whole text is one region, which is right
    for plain prose and wrong for anything else.

    Raises when the sweep found nothing to check. An empty corpus is a broken
    query; so is a corpus in which no page anywhere claims an absence, because
    the phrases below are ordinary editorial wording and a real collection uses
    them. Reporting "clean" for either would convert "not measured" into
    "measured clean".
    """
    if not pages:
        raise ValueError(
            "expired() got no pages: a sweep that examined nothing must fail "
            "loudly, not report clean")

    found = []
    checked = 0
    for title, text in sorted(pages.items()):
        regions = sentences(title, text or "") if sentences else [text or ""]
        for region in regions:
            for claim in absence_claims(region, profile):
                checked += 1
                names = candidate_names(claim.sentence)
                if extra_names:
                    for extra in extra_names(title, claim.sentence):
                        if extra not in names:
                            names.append(extra)
                live = [n for n in names if n in present]
                if live:
                    found.append((title, claim, live))

    if not checked:
        raise ValueError(
            "expired() found no absence claims in %d pages: the phrase list has "
            "stopped matching, which is more likely than a corpus that never "
            "says a page is missing" % len(pages))
    return found
