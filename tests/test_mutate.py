#!/usr/bin/env python3
"""Tests for research_core.mutate — injecting known defects.

These are the load-bearing tests of the detection eval. An operator that
silently fails to inject anything yields a perfect detection score from a
harness that measured nothing, and the score would look exactly like success.
Each operator is therefore asserted to have produced the defect it claims.
"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.mutate import (MutationError, fabricate_quote, load_corpus,
                                  paraphrase_quote)
from research_core.quoteaudit import audit

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", "corpus")


class MutateCase(unittest.TestCase):
    """Each test gets its own throwaway copy of the corpus."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.root = os.path.join(self.dir, "corpus")
        load_corpus(FIXTURES, self.root)

    def verdict(self, entity, row_id):
        for r in audit(self.root):
            if r["entity"] == entity and r["id"] == row_id:
                return r["verdict"]
        raise AssertionError(f"row {entity}/{row_id} not found after mutation")

    def ledger(self, entity):
        with open(os.path.join(self.root, entity, "sources.md")) as fh:
            return fh.read()


class TestLoadCorpus(MutateCase):
    def test_copy_is_independent_of_the_source(self):
        path = os.path.join(self.root, "Ashford_Rail_Corp", "sources.md")
        with open(path, "a") as fh:
            fh.write("\n| 9 | scribble | — | — | — | — | unknown | low |\n")
        original = os.path.join(FIXTURES, "Ashford_Rail_Corp", "sources.md")
        self.assertNotIn("scribble", open(original).read())

    def test_copy_starts_clean(self):
        self.assertEqual(
            [r["verdict"] for r in audit(self.root)],
            ["LOCAL"] * len(audit(self.root)))


class TestFabricateQuote(MutateCase):
    def test_row_stops_verifying(self):
        self.assertEqual(self.verdict("Ashford_Rail_Corp", "1"), "LOCAL")
        fabricate_quote(self.root, "Ashford_Rail_Corp", "1")
        self.assertEqual(self.verdict("Ashford_Rail_Corp", "1"), "MISSING")

    def test_injected_quote_is_in_no_snapshot(self):
        injected = fabricate_quote(self.root, "Ashford_Rail_Corp", "1")
        from research_core.quoteaudit import despace, snapshot_text
        for entity in os.listdir(self.root):
            body = snapshot_text(os.path.join(self.root, entity))
            if body:
                self.assertNotIn(despace(injected), body)

    def test_other_rows_are_untouched(self):
        fabricate_quote(self.root, "Ashford_Rail_Corp", "1")
        others = [r["verdict"] for r in audit(self.root)
                  if not (r["entity"] == "Ashford_Rail_Corp" and r["id"] == "1")]
        self.assertEqual(others, ["LOCAL"] * len(others))

    def test_is_deterministic(self):
        a = fabricate_quote(self.root, "Ashford_Rail_Corp", "1")
        load_corpus(FIXTURES, self.root)
        b = fabricate_quote(self.root, "Ashford_Rail_Corp", "1")
        self.assertEqual(a, b)

    def test_unknown_row_raises_rather_than_silently_doing_nothing(self):
        with self.assertRaises(MutationError):
            fabricate_quote(self.root, "Ashford_Rail_Corp", "99")

    def test_unknown_entity_raises(self):
        with self.assertRaises(MutationError):
            fabricate_quote(self.root, "No_Such_Entity", "1")


class TestParaphraseQuote(MutateCase):
    def test_row_stops_verifying(self):
        paraphrase_quote(self.root, "Ashford_Rail_Corp", "1")
        self.assertEqual(self.verdict("Ashford_Rail_Corp", "1"), "MISSING")

    def test_every_word_is_still_in_the_snapshot(self):
        # This is what distinguishes a paraphrase from a fabrication: the
        # content is real, the sentence is not. quoteaudit scores it 1.0.
        injected = paraphrase_quote(self.root, "Ashford_Rail_Corp", "1")
        from research_core.quoteaudit import coverage, snapshot_text
        body = snapshot_text(os.path.join(self.root, "Ashford_Rail_Corp"))
        self.assertEqual(coverage(injected, body), 1.0)

    def test_is_not_merely_the_original_quote(self):
        original = self.ledger("Ashford_Rail_Corp")
        injected = paraphrase_quote(self.root, "Ashford_Rail_Corp", "1")
        self.assertNotIn(f'"{injected}"', original)

    def test_is_deterministic(self):
        a = paraphrase_quote(self.root, "Ashford_Rail_Corp", "1")
        load_corpus(FIXTURES, self.root)
        b = paraphrase_quote(self.root, "Ashford_Rail_Corp", "1")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
