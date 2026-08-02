#!/usr/bin/env python3
"""Tests for research_core.citecheck — is a quote cited to the source that carries it?

The detection eval scored this defect class at 0/6: a real quote attached to the
wrong source passes every other check, because none of them asks which source
the quote came from.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.citecheck import (
    attribution, domain_of, normalize_url, read_sidecar,
)


class CorpusCase(unittest.TestCase):
    """Builds a throwaway corpus: one entity, two snapshots, two ledger rows."""

    LEDGER = ("| id | claim | quote | source page | url | tier | status | conf |\n"
              "|----|-------|-------|-------------|-----|------|--------|------|\n"
              '| 1 | depot opened | "the depot opened in 1913" | Gazette | '
              "URL_A | T2 | sourced | high |\n"
              '| 2 | works closed | "the works closed in 1987" | History | '
              "URL_B | T2 | sourced | high |")

    URL_A = "https://example.org/gazette-1911"
    URL_B = "https://example.org/continental-history"

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.root = os.path.join(self.dir, "corpus")
        self.entity = os.path.join(self.root, "Ashford_Rail_Corp")
        self.snaps = os.path.join(self.entity, "snapshots")
        os.makedirs(self.snaps)
        self._snapshot("a.html", "<p>the depot opened in 1913</p>")
        self._snapshot("b.html", "<p>the works closed in 1987</p>")
        self.write_ledger(self.URL_A, self.URL_B)

    def _snapshot(self, name, body):
        with open(os.path.join(self.snaps, name), "w") as fh:
            fh.write(body)

    def sidecar(self, name, url):
        with open(os.path.join(self.snaps, name + ".meta.json"), "w") as fh:
            json.dump({"url": url, "title": name}, fh)

    def write_ledger(self, url_a, url_b):
        text = self.LEDGER.replace("URL_A", url_a).replace("URL_B", url_b)
        with open(os.path.join(self.entity, "sources.md"), "w") as fh:
            fh.write(text)

    def verdicts(self):
        return {r["id"]: r["verdict"] for r in attribution(self.root)}


class TestNormalizeUrl(unittest.TestCase):
    def test_strips_scheme_www_and_trailing_slash(self):
        self.assertEqual(normalize_url("https://www.example.org/a/"),
                         normalize_url("http://example.org/a"))

    def test_keeps_the_query_string(self):
        # Two URLs differing only in query are different pages often enough
        # that discarding it would mask a real swap.
        self.assertNotEqual(normalize_url("https://example.org/a?id=1"),
                            normalize_url("https://example.org/a?id=2"))

    def test_is_case_insensitive_on_the_host_only(self):
        self.assertEqual(normalize_url("https://EXAMPLE.org/A"),
                         normalize_url("https://example.org/A"))
        self.assertNotEqual(normalize_url("https://example.org/A"),
                            normalize_url("https://example.org/a"))


class TestDomainOf(unittest.TestCase):
    def test_returns_host_without_www(self):
        self.assertEqual(domain_of("https://www.example.org/a"), "example.org")

    def test_returns_empty_for_a_non_url(self):
        self.assertEqual(domain_of("(same as #1)"), "")


class TestReadSidecar(CorpusCase):
    def test_returns_none_when_absent(self):
        self.assertIsNone(read_sidecar(os.path.join(self.snaps, "a.html")))

    def test_reads_the_url(self):
        self.sidecar("a.html", self.URL_A)
        self.assertEqual(
            read_sidecar(os.path.join(self.snaps, "a.html"))["url"], self.URL_A)

    def test_returns_none_on_malformed_json_rather_than_raising(self):
        with open(os.path.join(self.snaps, "a.html.meta.json"), "w") as fh:
            fh.write("{not json")
        self.assertIsNone(read_sidecar(os.path.join(self.snaps, "a.html")))


class TestExactAndMisattributed(CorpusCase):
    def test_correctly_cited_rows_are_exact(self):
        self.sidecar("a.html", self.URL_A)
        self.sidecar("b.html", self.URL_B)
        self.assertEqual(self.verdicts(), {"1": "EXACT", "2": "EXACT"})

    def test_a_swapped_citation_is_misattributed(self):
        self.sidecar("a.html", self.URL_A)
        self.sidecar("b.html", self.URL_B)
        self.write_ledger(self.URL_B, self.URL_A)     # the swap
        self.assertEqual(self.verdicts(), {"1": "MISATTRIBUTED",
                                           "2": "MISATTRIBUTED"})

    def test_reports_which_snapshot_it_attributed_to(self):
        self.sidecar("a.html", self.URL_A)
        self.sidecar("b.html", self.URL_B)
        by_id = {r["id"]: r["snapshot"] for r in attribution(self.root)}
        self.assertEqual(by_id["1"], "a.html")

    def test_url_differences_that_normalize_away_still_match(self):
        self.sidecar("a.html", "https://www.example.org/gazette-1911/")
        self.sidecar("b.html", self.URL_B)
        self.assertEqual(self.verdicts()["1"], "EXACT")

    def test_a_quote_in_no_snapshot_is_out_of_scope(self):
        # quoteaudit already reports these as MISSING. A row can only be
        # misattributed if its quote exists somewhere to be attributed.
        self.sidecar("a.html", self.URL_A)
        self.sidecar("b.html", self.URL_B)
        self.write_ledger(self.URL_A, self.URL_B)
        led = os.path.join(self.entity, "sources.md")
        text = open(led).read().replace("the works closed in 1987",
                                        "a sentence in no snapshot at all")
        open(led, "w").write(text)
        self.assertNotIn("2", self.verdicts())


class TestFallbackWithoutSidecars(CorpusCase):
    def test_domain_evidence_in_the_holding_snapshot_is_weak(self):
        # No sidecar. The snapshot carrying the quote mentions the cited
        # domain, so the attribution is consistent — but unproven.
        self._snapshot("a.html",
                       "<p>the depot opened in 1913</p>"
                       "<link rel='canonical' href='https://example.org/x'>")
        self.assertEqual(self.verdicts()["1"], "WEAK")

    def test_no_domain_evidence_anywhere_is_unrecorded(self):
        self._snapshot("a.html", "<p>the depot opened in 1913</p>")
        self.assertEqual(self.verdicts()["1"], "UNRECORDED")

    def test_a_same_domain_swap_is_invisible_without_a_sidecar(self):
        # Both fixture URLs are on example.org. This asserts the documented
        # limitation: domain evidence cannot distinguish two pages on one host,
        # so a swap between them reports WEAK rather than MISATTRIBUTED. If
        # this ever starts failing, the fallback got stronger — check why
        # before changing the assertion.
        self._snapshot("a.html",
                       "<p>the depot opened in 1913</p>"
                       "<link rel='canonical' href='https://example.org/x'>")
        self._snapshot("b.html",
                       "<p>the works closed in 1987</p>"
                       "<link rel='canonical' href='https://example.org/y'>")
        self.write_ledger(self.URL_B, self.URL_A)     # the swap
        self.assertEqual(self.verdicts()["1"], "WEAK")

    def test_a_cross_domain_swap_is_caught_even_without_a_sidecar(self):
        self._snapshot("a.html",
                       "<p>the depot opened in 1913</p>"
                       "<link rel='canonical' href='https://example.org/x'>")
        self.write_ledger("https://elsewhere.test/other", self.URL_B)
        self.assertEqual(self.verdicts()["1"], "UNRECORDED")

    def test_a_sidecar_on_one_snapshot_does_not_force_fallback_on_another(self):
        self.sidecar("a.html", self.URL_A)
        self.assertEqual(self.verdicts()["1"], "EXACT")
        self.assertIn(self.verdicts()["2"], ("WEAK", "UNRECORDED"))


if __name__ == "__main__":
    unittest.main()
