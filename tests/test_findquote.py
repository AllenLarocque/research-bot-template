#!/usr/bin/env python3
"""Tests for research_core.findquote's profile-driven sentence splitting.

findquote.py calls `main()` unmodified at import time (a pre-existing quirk,
not something this task's scope covers -- see fix-f2-f3-report.md). To import
it safely under any test runner, sys.argv is pinned to an empty-args shape
for the duration of the import so that one-time call takes the harmless
"print usage and return" branch, and its stdout is swallowed so test output
stays pristine.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_saved_argv = sys.argv
sys.argv = ["findquote.py"]
with contextlib.redirect_stdout(io.StringIO()):
    from research_core import findquote
sys.argv = _saved_argv

from research_core import srccache
from research_core.profile import load
from research_core.textutil import slug


class FindquoteCase(unittest.TestCase):
    """Shared fixture: a temporary cache directory bound as srccache.CACHE."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        original = srccache.CACHE
        srccache.CACHE = self.dir
        self.addCleanup(setattr, srccache, "CACHE", original)

    def write_manifest(self, titles):
        with open(os.path.join(self.dir, "manifest.json"), "w") as fh:
            json.dump({t: True for t in titles}, fh)

    def write_source(self, title, body):
        with open(os.path.join(self.dir, slug(title) + ".txt"), "w") as fh:
            fh.write(body)

    def _run(self, *args):
        old_argv = sys.argv
        sys.argv = ["findquote.py"] + list(args)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                findquote.main()
        finally:
            sys.argv = old_argv
        return buf.getvalue()


class TestMainMatching(FindquoteCase):
    """Core matching behaviour: AND across terms, case-insensitivity, and the
    25/420-char length window that keeps fragments and whole paragraphs out.
    """

    MATCH = "The harbour mill closed in 1975 after decades of operation here."
    NO_MATCH = "The harbour district saw no major industrial closures at all."
    SHORT = "The mill shut in 1975."  # 22 chars: at-or-under the 25-char floor
    LONG = ("This sentence about the harbour and the mill is deliberately "
            "padded with extra clauses and filler words so that its total "
            "length comfortably exceeds four hundred and twenty characters, "
            "the upper bound findquote enforces, which means even though it "
            "mentions both of the terms being searched for it must never be "
            "printed as a candidate because it blows past the ceiling that "
            "keeps whole paragraphs mistaken for sentences out of the results "
            "entirely, and this padding clause keeps going until it clears "
            "that four-hundred-and-twenty-character line by a comfortable "
            "margin so the test is not sensitive to exact boundary counting.")

    def test_prints_a_sentence_matching_all_terms(self):
        self.write_manifest(["Src"])
        self.write_source("Src", self.MATCH + " " + self.NO_MATCH)
        out = self._run("harbour", "mill")
        self.assertIn("[Src]", out)
        self.assertIn(self.MATCH, out)
        self.assertNotIn(self.NO_MATCH, out)
        self.assertIn("1 candidate sentence(s)", out)

    def test_matching_is_case_insensitive(self):
        self.write_manifest(["Src"])
        self.write_source("Src", self.MATCH)
        out = self._run("HARBOUR", "MILL")
        self.assertIn(self.MATCH, out)

    def test_all_terms_must_be_present_not_just_any(self):
        self.write_manifest(["Src"])
        self.write_source("Src", self.NO_MATCH)
        out = self._run("harbour", "mill")
        self.assertNotIn(self.NO_MATCH, out)
        self.assertIn("0 candidate sentence(s)", out)

    def test_sentences_at_or_under_the_25_char_floor_are_excluded(self):
        self.write_manifest(["Src"])
        self.write_source("Src", self.SHORT + " " + self.MATCH)
        out = self._run("mill", "shut")
        self.assertNotIn(self.SHORT, out)

    def test_sentences_at_or_over_the_420_char_ceiling_are_excluded(self):
        self.assertGreater(len(self.LONG), 420)
        self.write_manifest(["Src"])
        self.write_source("Src", self.LONG)
        out = self._run("harbour", "mill")
        self.assertIn("0 candidate sentence(s)", out)

    def test_titles_with_no_cached_text_are_skipped_without_error(self):
        self.write_manifest(["Ghost", "Src"])
        self.write_source("Src", self.MATCH)  # "Ghost" has no .txt on disk
        out = self._run("harbour", "mill")
        self.assertIn("[Src]", out)
        self.assertNotIn("[Ghost]", out)

    def test_titles_are_processed_in_sorted_order(self):
        self.write_manifest(["Beta", "Alpha"])
        self.write_source("Alpha", self.MATCH)
        self.write_source("Beta", self.MATCH)
        out = self._run("harbour", "mill")
        self.assertLess(out.index("[Alpha]"), out.index("[Beta]"))

    def test_no_terms_prints_usage_and_does_not_touch_the_cache(self):
        # No manifest.json is written for this test -- if main() reached
        # load_manifest() it would raise, so a clean pass proves the
        # no-args branch returns before touching the cache at all.
        out = self._run()
        self.assertIn("usage:", out)


class TestSourceFlag(FindquoteCase):
    """--source restricts the search to exactly one title."""

    MATCH = "The harbour mill closed in 1975 after decades of operation here."

    def test_source_flag_restricts_output_to_the_named_title(self):
        self.write_manifest(["Alpha", "Beta"])
        self.write_source("Alpha", self.MATCH)
        self.write_source("Beta", self.MATCH)
        out = self._run("--source", "Alpha", "harbour", "mill")
        self.assertIn("[Alpha]", out)
        self.assertNotIn("[Beta]", out)
        self.assertIn("1 candidate sentence(s)", out)

    def test_source_flag_reads_a_title_the_manifest_never_listed(self):
        # --source's title is used directly as a cache filename; it is never
        # checked against the manifest's own title list.
        self.write_manifest(["Alpha"])
        self.write_source("Ghost", self.MATCH)
        out = self._run("--source", "Ghost", "harbour", "mill")
        self.assertIn("[Ghost]", out)


class TestMainThreadsProfileToSplitSentences(unittest.TestCase):
    """The seam: findquote.main() must hand its profile to split_sentences.

    Same "Twp." construction as tests/test_srccache.py's threading test: a
    41-char first half that clears findquote's own 25-char floor alone, and
    a second half short enough that splitting at "Twp." produces two
    candidates while joining them at "Twp." produces one -- so which exact
    string gets printed proves whether the profile reached split_sentences,
    not just how many results came back.
    """

    PADDING = ("The company operated three facilities in the region for many "
               "years. Production continued through the post-war period "
               "without interruption. ") * 3
    TEXT = ("The township office building sits in Twp. It closed for good "
            "in 1975. ")

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        with open(os.path.join(self.dir, "manifest.json"), "w") as fh:
            json.dump({"Src": True}, fh)
        with open(os.path.join(self.dir, slug("Src") + ".txt"), "w") as fh:
            fh.write(self.PADDING + self.TEXT)
        original = srccache.CACHE
        srccache.CACHE = self.dir
        self.addCleanup(setattr, srccache, "CACHE", original)

    def _run(self, profile=None):
        old_argv = sys.argv
        sys.argv = ["findquote.py", "office"]
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                if profile is None:
                    findquote.main()
                else:
                    findquote.main(profile)
        finally:
            sys.argv = old_argv
        return buf.getvalue()

    def test_default_profile_splits_at_twp_so_the_tail_is_separate(self):
        out = self._run()
        self.assertIn("The township office building sits in Twp.", out)
        self.assertNotIn("It closed for good in 1975.", out)

    def test_profile_knowing_twp_keeps_the_sentence_whole(self):
        path = os.path.join(self.dir, "profile.toml")
        with open(path, "w") as fh:
            fh.write('name = "x"\nabbreviations = ["Twp."]\n')
        out = self._run(load(path))
        self.assertIn(
            "The township office building sits in Twp. It closed for good "
            "in 1975.", out)


if __name__ == "__main__":
    unittest.main()
