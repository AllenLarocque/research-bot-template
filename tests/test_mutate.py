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
                                  paraphrase_quote, shift_date, strip_anchor,
                                  swap_citation)
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


class TestSwapCitation(MutateCase):
    def test_row_now_cites_the_other_entitys_source(self):
        name = swap_citation(self.root, "Ashford_Rail_Corp", "1",
                             "Fairview_Works")
        self.assertIn(name, self.ledger("Ashford_Rail_Corp"))

    def test_quote_no_longer_matches_the_cited_source(self):
        # The quote still verifies somewhere in the corpus — it is real text —
        # but not against what the row now claims as its source.
        swap_citation(self.root, "Ashford_Rail_Corp", "1", "Fairview_Works")
        self.assertEqual(self.verdict("Ashford_Rail_Corp", "1"), "LOCAL")

    def test_raises_when_the_other_entity_has_no_rows(self):
        with self.assertRaises(MutationError):
            swap_citation(self.root, "Ashford_Rail_Corp", "1", "No_Such_Entity")

    def test_is_deterministic(self):
        a = swap_citation(self.root, "Ashford_Rail_Corp", "1", "Fairview_Works")
        load_corpus(FIXTURES, self.root)
        b = swap_citation(self.root, "Ashford_Rail_Corp", "1", "Fairview_Works")
        self.assertEqual(a, b)


class TestShiftDate(MutateCase):
    def test_claim_year_no_longer_matches_the_quote(self):
        old, new = shift_date(self.root, "Ashford_Rail_Corp", "1")
        led = self.ledger("Ashford_Rail_Corp")
        row = [l for l in led.splitlines() if l.strip().startswith("| 1 |")][0]
        claim, quote = row.split("|")[2], row.split("|")[3]
        self.assertIn(new, claim)
        self.assertIn(old, quote)
        self.assertNotIn(new, quote)

    def test_shift_is_large_enough_to_be_a_real_conflict(self):
        old, new = shift_date(self.root, "Ashford_Rail_Corp", "1")
        self.assertGreaterEqual(abs(int(new) - int(old)), 10)

    def test_raises_on_an_unknown_entity(self):
        with self.assertRaises(MutationError):
            shift_date(self.root, "No_Such_Entity", "1")

    def test_raises_when_the_claim_carries_no_year(self):
        # Give a row a year-free claim, then assert the guard fires rather
        # than the operator silently doing nothing.
        path = os.path.join(self.root, "Ashford_Rail_Corp", "sources.md")
        text = open(path).read().replace(
            "| 1 | Incorporated 1911 by Walter Ashgrove |",
            "| 1 | Incorporated by Walter Ashgrove |")
        open(path, "w").write(text)
        with self.assertRaises(MutationError):
            shift_date(self.root, "Ashford_Rail_Corp", "1")

    def test_is_deterministic(self):
        a = shift_date(self.root, "Ashford_Rail_Corp", "1")
        load_corpus(FIXTURES, self.root)
        b = shift_date(self.root, "Ashford_Rail_Corp", "1")
        self.assertEqual(a, b)


class TestStripAnchor(MutateCase):
    def test_claim_names_an_entity_no_quote_carries(self):
        name = strip_anchor(self.root, "Ashford_Rail_Corp", "1")
        led = self.ledger("Ashford_Rail_Corp")
        row = [l for l in led.splitlines() if l.strip().startswith("| 1 |")][0]
        self.assertIn(name, row.split("|")[2])
        self.assertNotIn(name, row.split("|")[3])

    def test_anchorcheck_sees_the_injected_name(self):
        # The detector this operator targets, driven directly.
        from research_core.anchorcheck import missing_anchors
        name = strip_anchor(self.root, "Ashford_Rail_Corp", "1")
        led = self.ledger("Ashford_Rail_Corp")
        row = [l for l in led.splitlines() if l.strip().startswith("| 1 |")][0]
        claim, quote = row.split("|")[2].strip(), row.split("|")[3].strip()
        miss = missing_anchors(claim, [quote], [], False)
        self.assertTrue(any(name.lower() in m.lower() for m in miss),
                        f"anchorcheck missed the injected name: {miss}")

    def test_is_deterministic(self):
        a = strip_anchor(self.root, "Ashford_Rail_Corp", "1")
        load_corpus(FIXTURES, self.root)
        b = strip_anchor(self.root, "Ashford_Rail_Corp", "1")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
