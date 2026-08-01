#!/usr/bin/env python3
"""Tests for research_core.srccache's profile-driven junk filtering."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.profile import DEFAULT, load
from research_core import srccache
from research_core.textutil import slug


class TestJunkIsProfileDriven(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)

    def write(self, body):
        path = os.path.join(self.dir, "profile.toml")
        with open(path, "w") as fh:
            fh.write(body)
        return path

    def test_general_junk_covers_site_navigation(self):
        self.assertTrue(DEFAULT.junk.search("Privacy policy"))

    def test_general_junk_does_not_name_a_regional_publisher(self):
        self.assertIsNone(DEFAULT.junk.search("Harbour Publishing"))

    def test_a_profile_can_add_a_publisher(self):
        p = load(self.write('name = "x"\njunk_patterns = ["Harbour Publ"]\n'))
        self.assertTrue(p.junk.search("Harbour Publishing"))


class TestSrcSentencesUsesTheProfile(unittest.TestCase):
    """The seam itself: the same cached text, filtered two ways.

    The three tests above assert on Profile.junk, which is the profile
    module's behaviour, not this module's — they pass whether or not
    src_sentences consults the profile at all. This one fails if it does not.
    """

    PADDING = ("The company operated three facilities in the region for many "
               "years. Production continued through the post-war period "
               "without interruption. ") * 3
    SENTENCE = ("The account of the strike was set down by Harbour Publishing "
                "in a later volume. ")

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        with open(os.path.join(self.dir, slug("Src") + ".txt"), "w") as fh:
            fh.write(self.PADDING + self.SENTENCE)
        # srccache binds CACHE at import from research_core.paths; rebind it
        # for the duration rather than reaching for an env var, which is read
        # once at import and cannot be changed afterwards.
        original = srccache.CACHE
        srccache.CACHE = self.dir
        self.addCleanup(setattr, srccache, "CACHE", original)

    def _quoted(self, profile=None):
        got = (srccache.src_sentences("Src") if profile is None
               else srccache.src_sentences("Src", profile))
        return any("Harbour Publishing" in s for s in got)

    def test_general_profile_offers_the_sentence_as_quotable(self):
        self.assertTrue(self._quoted())

    def test_a_profile_naming_the_publisher_filters_it_out(self):
        path = os.path.join(self.dir, "profile.toml")
        with open(path, "w") as fh:
            fh.write('name = "x"\njunk_patterns = ["Harbour Publ"]\n')
        self.assertFalse(self._quoted(load(path)))


class TestSrcSentencesThreadsProfileToSplitSentences(unittest.TestCase):
    """src_sentences takes a profile but must hand it to split_sentences too,
    or the profile's abbreviations never affect where sentences break.

    "Twp." is absent from the general base and multi-letter, so (per
    tests/test_textutil.py::TestSplitSentencesUsesProfile) it is the one
    abbreviation whose effect on splitting is observable here -- H.R.-shaped
    abbreviations are protected by split_sentences' own single-capital-letter
    guard regardless of the profile.

    The padding sentence is deliberately 34 chars ("The office sits in
    Twp." is not it -- see TEXT below): long enough to clear src_sentences'
    30-char floor on its own, while the second half ("It closed in 1975.")
    is deliberately kept under 30 chars so it is filtered out UNLESS the
    profile's abbreviation keeps the two halves joined into one candidate
    that clears the floor as a whole. That makes the observable difference
    which exact string comes back, not just a count.
    """

    PADDING = ("The company operated three facilities in the region for many "
               "years. Production continued through the post-war period "
               "without interruption. ") * 3
    TEXT = ("The township office building sits in Twp. It closed for good "
            "in 1975. ")

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        with open(os.path.join(self.dir, slug("Src") + ".txt"), "w") as fh:
            fh.write(self.PADDING + self.TEXT)
        original = srccache.CACHE
        srccache.CACHE = self.dir
        self.addCleanup(setattr, srccache, "CACHE", original)

    def test_default_profile_splits_at_twp_so_the_tail_is_dropped(self):
        got = srccache.src_sentences("Src")
        self.assertIn("The township office building sits in Twp.", got)
        self.assertNotIn(
            "The township office building sits in Twp. It closed for good "
            "in 1975.", got)

    def test_profile_knowing_twp_keeps_the_sentence_whole(self):
        path = os.path.join(self.dir, "profile.toml")
        with open(path, "w") as fh:
            fh.write('name = "x"\nabbreviations = ["Twp."]\n')
        got = srccache.src_sentences("Src", load(path))
        self.assertIn(
            "The township office building sits in Twp. It closed for good "
            "in 1975.", got)
        self.assertNotIn("The township office building sits in Twp.", got)


if __name__ == "__main__":
    unittest.main()
