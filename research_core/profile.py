#!/usr/bin/env python3
"""Domain vocabulary as data.

The general base lives here; a domain supplies an overlay in TOML. Merging is
add-only: a profile extends the base and can never remove from it, so reading
the base tells you the floor for every domain.

Read with tomllib (stdlib since 3.11) rather than YAML, which would be this
tree's only third-party dependency.

Loading fails loudly. Research run with no domain vocabulary does not error at
the point of use -- it silently reads "British Columbia" as a company name and
mis-attributes dates, which is worse than stopping.
"""
import re
import tomllib
from dataclasses import dataclass

# Every key a profile may set. An unknown key is an error, not a no-op: a
# typo'd vocabulary that silently does nothing is indistinguishable from a
# working one until the results are wrong.
KEYS = ("name", "abbreviations", "not_names", "titles", "owned_things",
        "junk_patterns")

# Sentence-splitter abbreviations that hold in any domain.
BASE_ABBREVIATIONS = ("U.S.", "Inc.", "Ltd.", "Co.", "Corp.", "St.", "Mt.",
                      "Dr.", "Mr.", "Ms.", "No.", "Jr.", "Sr.", "a.m.", "p.m.",
                      "approx.")

# Grammatical words that are never part of an entity name.
BASE_NOT_NAMES = frozenset("""
the a an in on at by for from its it he she they this that these those and but
or if when while after before during
""".split())

# Honorifics that are not personal names, anywhere.
BASE_TITLES = frozenset({"mr", "mrs", "ms", "dr", "sir", "president",
                         "the", "late"})

# Reference-list and site-navigation debris that must never be offered as a
# quote. Domain-specific publisher names belong in a profile, not here.
BASE_JUNK = (r"ISBN|ISSN|doi:|Retrieved \d|retrieved 20|Archived from|↑|"
             r"\[ edit \]|Wayback Machine|Cite \w+|www\.|http|@|"
             r"Special Collections|Oral History|\bp\. \d+|\bpp\. \d+|usw[.:]|"
             r"Privacy policy|Toggle the|Skip to|Search Search|Jump to|"
             r"Main menu|Sections News|Subscribe|Sign in|Log in|Newsletter|"
             r"All rights reserved|Table of contents|Read Edit|View history|"
             r"Download as PDF|About this capture|COLLECTED BY|\d+ captures|"
             r"success fail|TIMESTAMPS")

# Matches nothing. A base with no domain nouns must not match every word.
_MATCH_NOTHING = re.compile(r"(?!)")


class ProfileError(Exception):
    """A profile could not be read, parsed, or validated."""


@dataclass(frozen=True)
class Profile:
    name: str
    abbreviations: tuple
    not_names: frozenset
    titles: frozenset
    junk: re.Pattern
    owned_things: re.Pattern


DEFAULT = Profile(
    name="general",
    abbreviations=BASE_ABBREVIATIONS,
    not_names=BASE_NOT_NAMES,
    titles=BASE_TITLES,
    junk=re.compile(BASE_JUNK, re.I),
    owned_things=_MATCH_NOTHING,
)


def load(path):
    """Read a domain profile and merge it onto the general base."""
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as exc:
        raise ProfileError(f"cannot read profile {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"malformed profile {path}: {exc}") from exc

    unknown = sorted(set(data) - set(KEYS))
    if unknown:
        raise ProfileError(f"{path}: unknown key(s) {', '.join(unknown)}")
    if not data.get("name"):
        raise ProfileError(f"{path}: missing required key 'name'")

    # (?<!\w)/(?!\w) rather than \b on each side: \b only fires on a
    # transition between a word and a non-word character, so a word that
    # itself ENDS or STARTS on an escaped metacharacter -- "5(a)" ends in
    # ")", a non-word char -- would need its neighbour to be a word char
    # too, which "5(a) below" (a space) never is. The lookarounds only ask
    # that the character just outside the match not be a word character,
    # which is what "whole word, not embedded in a larger identifier"
    # actually means and holds regardless of what the word's own edges are.
    words = data.get("owned_things", [])
    owned = (re.compile(r"(?<!\w)(" + "|".join(re.escape(w) for w in words) + r")(?!\w)", re.I)
             if words else _MATCH_NOTHING)

    junk = BASE_JUNK
    if data.get("junk_patterns"):
        junk = junk + "|" + "|".join(data["junk_patterns"])

    return Profile(
        name=data["name"],
        abbreviations=BASE_ABBREVIATIONS + tuple(data.get("abbreviations", [])),
        not_names=BASE_NOT_NAMES | frozenset(data.get("not_names", [])),
        titles=BASE_TITLES | frozenset(data.get("titles", [])),
        junk=re.compile(junk, re.I),
        owned_things=owned,
    )
