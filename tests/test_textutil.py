#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.textutil import split_sentences, words, norm, slug
from research_core.profile import DEFAULT, load

# `plain()` is NOT tested here: despite the brief's interface sketch, it moved
# to research_mediawiki/retro.py (with narrative_span/page_sentences/
# sources_used), not research_core/, because its implementation recognises
# wikitext link/ref/template syntax directly -- see the module docstrings in
# research_core/textutil.py and research_mediawiki/retro.py for why.


class TestSplitSentences(unittest.TestCase):
    def test_splits_on_terminators(self):
        # The brief's original case here was `split_sentences("One. Two.
        # Three.") == ["One.", "Two.", "Three."]`, drafted from `grep '^def
        # '` without running it against the real implementation. Verified
        # (by file-path import of the untouched original
        # /dossiers/.../scripts/retro.py) that split_sentences silently drops
        # ANY candidate whose stripped text is <=20 chars
        # (`if len(seg.strip()) > 20`) -- "One." (4 chars), "Two." (4),
        # "Three." (6) and the whole 17-char string all fail that floor, so
        # the real return value is [], not three spans. This is a
        # pre-existing behaviour (confirmed unchanged by this refactor, see
        # differential below), not something to fix inside a split -- recorded
        # here as a follow-up.
        self.assertEqual(split_sentences("One. Two. Three."), [])
        # A case that actually clears the length floor splits as expected.
        text = "The mill closed in 1983 after decades. It never reopened again."
        spans = split_sentences(text)
        self.assertEqual([text[a:b] for a, b in spans],
                          ["The mill closed in 1983 after decades.",
                           " It never reopened again."])

    def test_short_candidate_sentences_are_dropped(self):
        # Direct documentation of the >20-char floor: two short "sentences"
        # never produce two spans.
        self.assertEqual(split_sentences("Short. Bits."), [])

    def test_keeps_abbreviated_initials_intact_hr(self):
        # H.R. MacMillan, W.J. Van Dusen, E.P. Taylor are all real entity
        # names in this corpus -- the ABBREV list and the "\b[A-Z]\.$" initials
        # check exist specifically so a name like this is not cut in half.
        self.assertEqual(len(split_sentences("H.R. MacMillan founded it.")), 1)

    def test_keeps_abbreviated_initials_intact_wj(self):
        self.assertEqual(
            len(split_sentences("W.J. Van Dusen ran the mill for decades.")), 1)

    def test_keeps_abbreviated_initials_intact_ep(self):
        self.assertEqual(
            len(split_sentences("E.P. Taylor invested heavily in it.")), 1)

    def test_decimal_number_does_not_split(self):
        text = "This is a decimal 3.14 in the middle of a long sentence here."
        self.assertEqual(len(split_sentences(text)), 1)

    def test_ellipsis_does_not_split(self):
        text = "Ellipsis here... and then more text follows in one sentence."
        self.assertEqual(len(split_sentences(text)), 1)

    def test_quote_ending_sentence_splits(self):
        text = ('She said "This is quoted text." and walked away into '
                 'the evening.')
        spans = split_sentences(text)
        self.assertEqual(len(spans), 2)

    def test_empty_input(self):
        self.assertEqual(split_sentences(""), [])


class TestSplitSentencesUsesProfile(unittest.TestCase):
    # "Twp." rather than one of the five domain abbreviations the profile will
    # carry: split_sentences has a second, independent guard that skips any
    # single capital letter followed by a period ("skip decimals / initials"),
    # and H.R./W.J./E.P./J.H./B.C. all match that shape. They are therefore
    # protected whether or not the abbreviation list mentions them, so none of
    # them can demonstrate that this seam works. "Twp." is multi-letter and
    # absent from the general base, so its presence in a profile is observable.
    TEXT = "The township office sits in Twp. It finally closed in 1975."

    def test_general_profile_does_not_know_the_abbreviation(self):
        self.assertEqual(len(split_sentences(self.TEXT)), 2)

    def test_a_profile_supplying_the_abbreviation_prevents_the_split(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "profile.toml")
            with open(path, "w") as fh:
                fh.write('name = "x"\nabbreviations = ["Twp."]\n')
            self.assertEqual(len(split_sentences(self.TEXT, load(path))), 1)


class TestWords(unittest.TestCase):
    def test_drops_punctuation_and_stopwords(self):
        # The brief's version (`words("the mill, closed.") == ["the", "mill",
        # "closed"]`) forgot that "the" is itself in STOP and gets dropped --
        # confirmed against the original implementation.
        self.assertEqual(words("the mill, closed."), ["mill", "closed"])


class TestNorm(unittest.TestCase):
    def test_collapses_whitespace_and_case(self):
        self.assertEqual(norm("  The   MILL  "), "the mill")


class TestSlug(unittest.TestCase):
    def test_underscores_spaces(self):
        self.assertEqual(slug("Powell River"), "Powell_River")


if __name__ == "__main__":
    unittest.main(verbosity=2)
