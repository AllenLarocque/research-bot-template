#!/usr/bin/env python3
"""Flag sentences that assert an anchor none of their citations contains.

Vocabulary-overlap checks catch a quote that is simply about something else.
They do not catch the more dangerous case: a quote that is plainly on-topic
and shares most of its words, but is silent on the specific thing the
sentence asserts.

The signal is an ANCHOR -- a year, a figure, or a multi-word proper noun --
that the sentence states and its quotes do not. Three rules keep this usable:

  * anchors are checked against the UNION of every quote on the sentence,
    since a sentence with three citations is supported by all three together;
  * names that appear in the titles of the sentence's own source pages are
    ignored, because in-text attribution of a source's own name is not an
    unsourced claim;
  * markup is expected to already be stripped from the sentence text before
    it reaches these functions -- callers are responsible for that.

It still cannot decide support. It ranks pairs for reading.
"""
import re

from research_core.profile import DEFAULT


def proper_nouns(s, profile=DEFAULT):
    """Multi-word capitalised runs, lowercased. Single words are too noisy."""
    out = set()
    for m in re.finditer(r"\b([A-Z][a-zA-Z&.\-']+(?:\s+[A-Z][a-zA-Z&.\-']+)+)", s):
        name = m.group(1).lower()
        if all(w in profile.not_names for w in name.split()):
            continue
        out.add(name)
    return out


def years(s):
    return set(re.findall(r"\b(1[6-9]\d{2}|20\d{2})\b", s))


def figures(s):
    return {re.sub(r"[,\s]", "", x) for x in re.findall(r"\b\d[\d,]{2,}(?:\.\d+)?\b", s)}


def flat(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s.lower())).strip()


# Pairs a source may write differently from an encyclopedia sentence.
EQUIV = [("united states", "u s"), ("united states", "usa"),
         ("great britain", "britain"), ("saint", "st")]


def name_present(name, haystack, profile=DEFAULT):
    """Is this name carried by the text, allowing for the ways sources shorten names?

    A source almost never repeats a name the way an encyclopedia sentence does.
    Three equivalences keep the check honest without crying wolf:
      * the full string ("alex macdonald");
      * an acronym of its initials ("afw" for "amalgamated federation of
        workers"), which is how unions and companies are actually written;
      * the last substantial word ("smith" for "premier jane q. smith"),
        because a surname or a distinctive final word carries the identity.
    """
    fn = flat(name)
    if fn in haystack:
        return True
    for a, b in EQUIV:
        if a in fn and b in haystack:
            return True
    words = [w for w in fn.split() if w not in profile.titles and w != "s"]
    if len(words) > 1:
        acronym = "".join(w[0] for w in words)
        if len(acronym) >= 2 and re.search(r"\b%s\b" % re.escape(acronym), haystack):
            return True
    if words and len(words[-1]) >= 4 and re.search(r"\b%s" % re.escape(words[-1]), haystack):
        return True
    return False


def missing_anchors(claim, quotes, source_titles, want_figures, profile=DEFAULT):
    """Anchors the claim asserts that no quote carries."""
    joined = flat(" ".join(quotes))
    titles = flat(" ".join(source_titles))
    qy = years(" ".join(quotes))
    qf = figures(" ".join(quotes))
    miss = []
    for n in proper_nouns(claim, profile):
        if name_present(n, joined, profile) or name_present(n, titles, profile):
            continue
        miss.append("name:" + n)
    # A source titled with a date dates its own claim; so does a source page
    # whose title carries the date of the issue it transcribes.
    ty = years(" ".join(source_titles))
    for y in years(claim) - qy - ty:
        miss.append("year:" + y)
    if want_figures:
        for f in figures(claim) - qf - years(claim):
            miss.append("figure:" + f)
    return miss
