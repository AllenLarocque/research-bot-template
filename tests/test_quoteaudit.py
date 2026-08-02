#!/usr/bin/env python3
"""Tests for research_core.quoteaudit — auditing ledger quotes against snapshots.

Motivated by a fabricated quote found on 2026-07-31: a dossier attributed a
sentence to a source whose captured snapshot does not contain it anywhere. The
claim had already been demoted on the page, but the invented quote stayed in
the ledger, where it reads as genuine provenance to anything re-checking the
file.

The audit is deliberately space-insensitive. Scanned-newspaper OCR breaks words
across column boundaries ("government offi cials"), so a space-sensitive check
reports text that is demonstrably present as missing — 13 false positives in
the first sweep of the corpus.
"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.quoteaudit import (
    despace, verbatim, ledger_quotes, classify, coverage,
    snapshot_text, snapshot_texts, audit,
)

# An 8-column ledger and the older 6-column table that superseded ledgers keep
# below them. The quote sits at cell index 2 in both; the URL column does not.
LEDGER_8 = (
    "| id | claim | quote | source page | url | tier | status | confidence |\n"
    "|----|-------|-------|-------------|-----|------|--------|------------|\n"
    '| 1 | Founded 1911 | "was formed in 1911 by the lumberman" | EoBC | '
    "https://example.org/a | T2 | sourced | high |\n"
    "| 2 | HQ unknown | — | — | — | — | unknown | low |"
)

LEDGER_6 = (
    "| # | Claim | Supporting quote | URL | Archive | Confidence |\n"
    "|---|-------|------------------|-----|---------|------------|\n"
    '| 1 | Merged 1951 | "merged with the export company in 1951" | '
    "https://example.org/b | (archive) | high |\n"
    '| 2 | Signed the papers | "signed the merger documents that October" | '
    "(same as #1) | (same) | medium |"
)


class TestDespace(unittest.TestCase):
    def test_strips_spaces_and_punctuation(self):
        self.assertEqual(despace("Government officials, today!"),
                         "governmentofficialstoday")

    def test_ocr_column_break_matches_intact_word(self):
        self.assertEqual(despace("government offi cials"),
                         despace("government officials"))


class TestVerbatim(unittest.TestCase):
    def test_finds_quote_present_in_body(self):
        body = despace("The mill opened in 1957 and employed 300 people.")
        self.assertTrue(verbatim("opened in 1957 and employed 300", body))

    def test_rejects_quote_absent_from_body(self):
        body = despace("The mill opened in 1957 and employed 300 people.")
        self.assertFalse(
            verbatim("signed the merger documents as his last act", body))

    def test_survives_ocr_word_split_in_the_body(self):
        body = despace("vancouver cp government offi cials today succeeded")
        self.assertTrue(verbatim("government officials today succeeded", body))

    def test_requires_every_ellipsis_separated_part(self):
        body = despace("Fletcher Challenge did many things in 1987.")
        self.assertFalse(
            verbatim("In 1987, Fletcher Challenge … acquired a stake", body))

    def test_accepts_when_all_ellipsis_parts_present(self):
        body = despace("In 1987 Fletcher Challenge grew, and acquired a stake.")
        self.assertTrue(
            verbatim("In 1987 Fletcher Challenge … acquired a stake", body))

    def test_ignores_fragments_shorter_than_the_floor(self):
        # A 3-character fragment would match almost any body by accident.
        body = despace("nothing relevant here at all")
        self.assertFalse(verbatim("abc", body))


class TestLedgerQuotes(unittest.TestCase):
    def test_reads_quote_and_url_from_the_8_column_ledger(self):
        rows = ledger_quotes(LEDGER_8)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "1")
        self.assertEqual(rows[0]["quote"], "was formed in 1911 by the lumberman")
        self.assertEqual(rows[0]["url"], "https://example.org/a")

    def test_skips_rows_with_no_quote(self):
        self.assertEqual([r["id"] for r in ledger_quotes(LEDGER_8)], ["1"])

    def test_reads_the_6_column_superseded_table(self):
        rows = ledger_quotes(LEDGER_6)
        self.assertEqual(rows[0]["quote"],
                         "merged with the export company in 1951")
        self.assertEqual(rows[0]["url"], "https://example.org/b")

    def test_same_as_notation_inherits_the_previous_url(self):
        rows = ledger_quotes(LEDGER_6)
        self.assertEqual(rows[1]["url"], "https://example.org/b")

    def test_flags_an_already_retracted_row(self):
        md = ('| 8 | **RETRACTED — QUOTE NOT IN SOURCE** He signed | '
              '"signed the merger documents" | W | https://example.org/c | '
              "T3 | unknown | medium |")
        self.assertTrue(ledger_quotes(md)[0]["retracted"])

    def test_does_not_flag_an_ordinary_row_as_retracted(self):
        self.assertFalse(ledger_quotes(LEDGER_8)[0]["retracted"])

    def test_reads_every_quoted_span_in_one_cell(self):
        md = ('| 5 | Two things | "the camp opened in 1936" / '
              '"the river flows west" | W | https://example.org/d | T3 | '
              "sourced | medium |")
        self.assertEqual([r["quote"] for r in ledger_quotes(md)],
                         ["the camp opened in 1936", "the river flows west"])


class TestClassify(unittest.TestCase):
    QUOTE = "opened in 1957 and employed 300"
    BODY = "The mill opened in 1957 and employed 300 people."

    def test_no_snapshots_at_all_is_unverifiable(self):
        self.assertEqual(classify(self.QUOTE, None, despace(self.BODY)),
                         "NOSNAP")

    def test_present_in_own_snapshots(self):
        self.assertEqual(
            classify(self.QUOTE, despace(self.BODY), despace(self.BODY)),
            "LOCAL")

    def test_present_only_in_another_dossiers_snapshots(self):
        self.assertEqual(
            classify(self.QUOTE, despace("unrelated text"), despace(self.BODY)),
            "GLOBAL")

    def test_absent_everywhere(self):
        self.assertEqual(
            classify(self.QUOTE, despace("unrelated"), despace("also unrelated")),
            "MISSING")


class TestCoverage(unittest.TestCase):
    def test_all_content_words_present_though_not_contiguous(self):
        # The Canfor case: every content word is in the source, as separate
        # sentences. That is a paraphrase set in quotation marks, not an
        # invented fact — a different and lesser defect.
        body = despace("Pattison acquired the company. Control passed after "
                       "a proxy fight.")
        self.assertEqual(coverage("Pattison acquired control in a proxy fight",
                                  body), 1.0)

    def test_no_content_words_present(self):
        self.assertEqual(coverage("ended production on April",
                                  despace("entirely unrelated wording")), 0.0)

    def test_empty_quote_scores_zero_rather_than_dividing_by_zero(self):
        self.assertEqual(coverage("a an the", despace("anything")), 0.0)


class TestSnapshotText(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def _entity(self, name, ledger=None, snapshots=None):
        d = os.path.join(self.root, name)
        os.makedirs(d)
        if ledger is not None:
            with open(os.path.join(d, "sources.md"), "w") as fh:
                fh.write(ledger)
        if snapshots is not None:
            os.makedirs(os.path.join(d, "snapshots"))
            for fn, body in snapshots.items():
                with open(os.path.join(d, "snapshots", fn), "w") as fh:
                    fh.write(body)
        return d

    def test_returns_none_when_no_snapshots_directory(self):
        self.assertIsNone(snapshot_text(self._entity("A", ledger="")))

    def test_returns_none_when_snapshots_directory_is_empty(self):
        self.assertIsNone(snapshot_text(self._entity("B", ledger="",
                                                     snapshots={})))

    def test_strips_markup_and_decodes_entities(self):
        d = self._entity("C", ledger="", snapshots={
            "s.html": "<p>Bloedel &amp; Welch<script>junk()</script></p>"})
        body = snapshot_text(d)
        self.assertIn(despace("Bloedel & Welch"), body)
        self.assertNotIn("junk", body)

    def test_concatenates_every_snapshot_file(self):
        d = self._entity("D", ledger="", snapshots={
            "one.html": "<p>first document</p>",
            "two.html": "<p>second document</p>"})
        body = snapshot_text(d)
        self.assertIn(despace("first document"), body)
        self.assertIn(despace("second document"), body)


class TestAudit(unittest.TestCase):
    LEDGER = ('| id | claim | quote | source | url | tier | status | conf |\n'
              '| 1 | present | "the mill opened in 1957" | S | '
              "https://example.org/a | T2 | sourced | high |\n"
              '| 2 | absent | "signed the merger documents that October" | S | '
              "https://example.org/a | T2 | sourced | high |")

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def _entity(self, name, ledger, snapshot=None):
        d = os.path.join(self.root, name)
        os.makedirs(os.path.join(d, "snapshots") if snapshot else d)
        with open(os.path.join(d, "sources.md"), "w") as fh:
            fh.write(ledger)
        if snapshot:
            with open(os.path.join(d, "snapshots", "s.html"), "w") as fh:
                fh.write(snapshot)

    def test_verdicts_per_row(self):
        self._entity("Mill", self.LEDGER, "<p>The mill opened in 1957.</p>")
        found = {r["id"]: r["verdict"] for r in audit(self.root)}
        self.assertEqual(found, {"1": "LOCAL", "2": "MISSING"})

    def test_evidence_filed_under_another_entity_is_global(self):
        self._entity("Mill", self.LEDGER, "<p>nothing useful</p>")
        self._entity("Other", "", "<p>The mill opened in 1957.</p>")
        found = {r["id"]: r["verdict"] for r in audit(self.root)}
        self.assertEqual(found["1"], "GLOBAL")

    def test_entity_without_snapshots_is_unverifiable(self):
        self._entity("Mill", self.LEDGER)
        self.assertEqual({r["verdict"] for r in audit(self.root)}, {"NOSNAP"})

    def test_skips_underscore_prefixed_bookkeeping_directories(self):
        self._entity("_runs", self.LEDGER, "<p>The mill opened in 1957.</p>")
        self.assertEqual(audit(self.root), [])

    def test_reports_entity_and_coverage_on_each_row(self):
        self._entity("Mill", self.LEDGER, "<p>The mill opened in 1957.</p>")
        row = [r for r in audit(self.root) if r["id"] == "1"][0]
        self.assertEqual(row["entity"], "Mill")
        self.assertEqual(row["coverage"], 1.0)


class TestSnapshotTexts(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.snapdir = os.path.join(self.root, "snapshots")
        os.makedirs(self.snapdir)

    def _write(self, name, body):
        with open(os.path.join(self.snapdir, name), "w") as fh:
            fh.write(body)

    def test_returns_none_when_no_snapshots_directory(self):
        empty = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, empty)
        self.assertIsNone(snapshot_texts(empty))

    def test_keys_are_filenames_and_values_are_that_file_only(self):
        self._write("a.html", "<p>the depot opened in 1913</p>")
        self._write("b.html", "<p>the works closed in 1987</p>")
        got = snapshot_texts(self.root)
        self.assertEqual(sorted(got), ["a.html", "b.html"])
        self.assertIn(despace("the depot opened in 1913"), got["a.html"])
        self.assertNotIn(despace("the depot opened in 1913"), got["b.html"])

    def test_sidecars_are_not_snapshots(self):
        # A .meta.json in snapshots/ describes a capture; it is not one. Left
        # in, its JSON would be despaced into the body and a quote could
        # appear to verify against a file that is not a capture at all.
        self._write("a.html", "<p>the depot opened in 1913</p>")
        self._write("a.html.meta.json",
                    '{"url": "https://example.org/x", "title": "a distinctive title"}')
        got = snapshot_texts(self.root)
        self.assertEqual(sorted(got), ["a.html"])
        self.assertNotIn(despace("a distinctive title"),
                         snapshot_text(self.root))

    def test_snapshot_text_still_joins_every_snapshot(self):
        self._write("a.html", "<p>the depot opened in 1913</p>")
        self._write("b.html", "<p>the works closed in 1987</p>")
        joined = snapshot_text(self.root)
        self.assertIn(despace("the depot opened in 1913"), joined)
        self.assertIn(despace("the works closed in 1987"), joined)


if __name__ == "__main__":
    unittest.main()
