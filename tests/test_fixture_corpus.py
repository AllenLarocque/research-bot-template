#!/usr/bin/env python3
"""The fixture corpus must be clean before anything is planted in it.

A detection eval measures how many injected defects are caught. If the corpus
carries defects of its own, every score is inflated by them and the number
means nothing. This is the false-positive control, and it runs first.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.citecheck import attribution
from research_core.quoteaudit import audit

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "fixtures", "corpus")


class TestCorpusIsClean(unittest.TestCase):
    def setUp(self):
        self.rows = audit(CORPUS)

    def test_corpus_has_rows(self):
        # A corpus that parses to nothing would pass every other assertion here.
        self.assertGreaterEqual(len(self.rows), 6)

    def test_every_quote_verifies_locally(self):
        bad = [(r["entity"], r["id"], r["verdict"]) for r in self.rows
               if r["verdict"] != "LOCAL"]
        self.assertEqual(bad, [], f"rows not verifying against their own "
                                  f"snapshots: {bad}")

    def test_no_row_is_marked_retracted(self):
        self.assertEqual([r["id"] for r in self.rows if r["retracted"]], [])

    def test_more_than_one_entity(self):
        self.assertGreaterEqual(len({r["entity"] for r in self.rows}), 2)


class TestCorpusAttribution(unittest.TestCase):
    def test_every_clean_row_is_exactly_attributed(self):
        bad = [(r["entity"], r["id"], r["verdict"])
               for r in attribution(CORPUS) if r["verdict"] != "EXACT"]
        self.assertEqual(bad, [], f"rows without exact attribution: {bad}")

    def test_attribution_covers_every_row(self):
        self.assertEqual(len(attribution(CORPUS)), len(audit(CORPUS)))


if __name__ == "__main__":
    unittest.main()
