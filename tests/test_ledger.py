#!/usr/bin/env python3
"""Tests for research_core.ledger — the claim-ledger half of the old verify.py.

Ported from /dossiers/_skillset/forestwiki-research/scripts/test_verify.py.
Only the markdown-ledger and already-parsed-relationship-dict tests live here;
everything that needs wikitext ({{Cite}}, <ref>, {{Relationship}} markup, or
rendered HTML) followed missing_templates/parse_relationships/etc into
tests/test_verify_adapter.py.

check_ai_verified's tests were rewritten (not ported verbatim): the original
called `check_ai_verified(parse_relationships(WT))`, composing wikitext
parsing with the pure check. Task 9 changed check_ai_verified to take a list
of already-parsed relationship dicts directly (parse_relationships now lives
in research_mediawiki/verify.py and is not research_core's concern), so these tests
build the dicts by hand instead of parsing wikitext to get them. The
composition of the two is still exercised, in
tests/test_verify_adapter.py::TestAiVerifiedComposition.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.ledger import parse_ledger, check_ledger_coverage, check_ai_verified

LEDGER = """| id | claim | quote | source page | url | tier | status | confidence |
|1|Founded 1919|"launched in 1919"|Canadian Encyclopedia — X|http://x|T2|sourced|high|
|2|HQ Vancouver||—|—|—|unknown|low|"""


class TestParseLedger(unittest.TestCase):
    def test_parse_ledger(self):
        rows = parse_ledger(LEDGER)
        self.assertEqual(rows[0]["status"], "sourced")
        self.assertEqual(rows[0]["quote"], '"launched in 1919"')

    def test_parse_ledger_skips_separator_row(self):
        md = ("| id | claim | quote | source page | url | tier | status | confidence |\n"
              "|----|-------|-------|-------------|-----|------|--------|------------|\n"
              '|1|c|"q"|X|u|T2|sourced|high|')
        self.assertEqual(len(parse_ledger(md)), 1)


class TestLedgerCoverage(unittest.TestCase):
    def test_ledger_coverage_ok(self):
        self.assertEqual(check_ledger_coverage({"Canadian Encyclopedia — X"},
                                               parse_ledger(LEDGER)), [])

    def test_ledger_coverage_flags_orphan_cite(self):
        errs = check_ledger_coverage({"Ghost Source"}, parse_ledger(LEDGER))
        self.assertTrue(any("Ghost Source" in e for e in errs))

    def test_ledger_coverage_flags_sourced_without_quote(self):
        bad = parse_ledger("| id | claim | quote | source page | url | tier | status | confidence |\n"
                           "|1|c||X|u|T2|sourced|high|")
        self.assertTrue(any("no verbatim quote" in e for e in check_ledger_coverage(set(), bad)))


class TestAiVerified(unittest.TestCase):
    """The two-source rule (research/CLAUDE.md): verification=ai-verified is
    legitimate only when 2+ independent sources corroborate. check_ai_verified
    now takes already-parsed relationship dicts rather than wikitext."""

    def test_flags_single_source_relationship(self):
        rels = [
            {"predicate": "acquired", "object": "Bar",
             "sources": ["Wikipedia — Y", "SEC — Z"], "verification": "ai-verified"},
            {"predicate": "owned_by", "object": "Baz",
             "sources": ["Wikipedia — Y"], "verification": "ai-verified"},
        ]
        errs = check_ai_verified(rels)
        self.assertTrue(any("owned_by → Baz" in e and "1 source" in e for e in errs))
        self.assertFalse(any("acquired → Bar" in e for e in errs))

    def test_passes_with_two_or_more_sources(self):
        rels = [{"predicate": "acquired", "object": "Bar",
                 "sources": ["Wikipedia — Y", "SEC — Z"], "verification": "ai-verified"}]
        self.assertEqual(check_ai_verified(rels), [])

    def test_non_ai_verified_relationship_is_never_flagged(self):
        rels = [{"predicate": "owned_by", "object": "Baz",
                 "sources": ["Wikipedia — Y"], "verification": "unverified"}]
        self.assertEqual(check_ai_verified(rels), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
