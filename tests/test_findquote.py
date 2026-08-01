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
