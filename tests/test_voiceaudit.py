#!/usr/bin/env python3
"""Core-side tests: patterns, severities, offsets, and the empty-corpus raise.

Anything that needs wikitext to state -- what gets skipped, which surface an
offset sits on -- is tested in the wiki adapter against voicemarkup, because
research_core is not allowed to know what a <ref> is. test_layering enforces
that, and caught this module's first draft doing it.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.voiceaudit import (
    ERROR, PROSE, WARN, Finding, audit, blank, counts, scan, worst_first,
)


def names(findings):
    return set(f.name for f in findings)


class TestErrorPatterns(unittest.TestCase):
    """Spans that need no judgment: the text is naming its own machinery."""

    def test_briefing_file(self):
        self.assertIn("names-briefing",
                      names(scan("which is what CLAUDE.md means by that")))

    def test_corpus(self):
        self.assertIn("names-corpus",
                      names(scan("it adds a great deal the corpus did not have")))

    def test_dossier(self):
        self.assertIn("names-dossier",
                      names(scan("marked as such in this entity's dossier")))

    def test_this_wiki(self):
        self.assertIn("names-wiki",
                      names(scan("the connection to the rest of this wiki")))

    def test_apparatus(self):
        self.assertIn("names-apparatus",
                      names(scan("No relationship row is written here.")))

    def test_progress_note(self):
        self.assertIn("progress-note",
                      names(scan("the first source on this page that is not Wikipedia")))

    def test_ordinary_prose_survives_the_error_set(self):
        # A checker that fires on normal sentences gets switched off.
        clean = ("The Somass Sawmill opened in 1935 and was renamed in 1953 "
                 "after a merger between logging companies. Western Forest "
                 "Products curtailed it indefinitely in 2017.")
        self.assertEqual([f for f in scan(clean) if f.severity == ERROR], [])


class TestWarnPatterns(unittest.TestCase):
    """Usually narration, sometimes a legitimate scope note."""

    def test_page_self(self):
        self.assertIn("page-self", names(scan("This page is about the man.")))

    def test_rests_on(self):
        self.assertIn("rests-on",
                      names(scan("Everything above rests on a single tertiary source")))

    def test_search_limits(self):
        self.assertIn("search-limits",
                      names(scan("Nothing read for it gives the forest cover")))

    def test_bare_snapshot_is_only_a_warning(self):
        # "a snapshot of the industry in 1953" is ordinary English. The
        # directory name is not.
        found = scan("a snapshot of the industry in 1953")
        self.assertEqual([f.severity for f in found], [WARN])
        self.assertIn("names-dossier", names(scan("copied from snapshots/foo.html")))

    def test_a_warn_never_blocks_on_its_own(self):
        self.assertEqual([f for f in scan("This page is about the man.")
                          if f.severity == ERROR], [])


class TestSkip(unittest.TestCase):
    """The argument that decides whether this check can do damage."""

    def test_a_skipped_span_is_not_flagged(self):
        text = "quoted: the wiki of record. plain: the corpus."
        self.assertEqual(names(scan(text, skip=[(0, 27)])), {"names-corpus"})

    def test_skipping_nothing_is_the_documented_default(self):
        # scan() cannot see markup, so it cannot infer what to skip. The default
        # flags everything, visibly, rather than guessing.
        self.assertEqual(len(scan("the corpus")), 1)

    def test_offsets_survive_skipping(self):
        # Blanking, not deleting: a delete-based mask slides every later offset
        # and points the caller at the wrong sentence.
        text = "xxxxxxxxxx\nthe corpus"
        found = scan(text, skip=[(0, 10)])
        self.assertEqual(found[0].line, 2)
        self.assertEqual(text[found[0].start:found[0].end], "corpus")

    def test_blank_preserves_length(self):
        self.assertEqual(len(blank("abcdef", [(1, 3)])), 6)
        self.assertEqual(blank("abcdef", [(1, 3)]), "a  def")

    def test_blank_tolerates_out_of_range_spans(self):
        self.assertEqual(blank("abc", [(-5, 99)]), "   ")


class TestSurface(unittest.TestCase):
    def test_default_surface_is_prose(self):
        self.assertEqual([f.where for f in scan("the corpus")], [PROSE])

    def test_caller_supplies_the_label(self):
        found = scan("the corpus", surface=lambda offset: "heading")
        self.assertEqual([f.where for f in found], ["heading"])


class TestAudit(unittest.TestCase):
    def test_clean_page_is_omitted(self):
        results = audit({"Clean": "The mill opened in 1935.", "Dirty": "the corpus"})
        self.assertEqual(list(results), ["Dirty"])

    def test_empty_corpus_raises_rather_than_reporting_clean(self):
        # The failure this project has already paid for: a check that read zero
        # rows and called the corpus examined.
        with self.assertRaises(ValueError):
            audit({})

    def test_one_empty_page_is_not_a_broken_query(self):
        self.assertEqual(audit({"Empty": ""}), {})

    def test_scanner_is_pluggable(self):
        # How the wiki adapter injects markup awareness without core knowing.
        seen = []

        def scanner(text):
            seen.append(text)
            return scan(text, skip=[(0, len(text))])

        self.assertEqual(audit({"A": "the corpus"}, scanner=scanner), {})
        self.assertEqual(seen, ["the corpus"])

    def test_counts(self):
        self.assertEqual(counts(audit({"A": "the corpus and this page"})),
                         {ERROR: 1, WARN: 1})

    def test_worst_first_ranks_by_error_count(self):
        results = audit({
            "few": "this page",
            "many": "the corpus, the dossier, this wiki",
        })
        self.assertEqual(worst_first(results)[0], "many")


class TestFinding(unittest.TestCase):
    def test_findings_are_deduplicated_by_position(self):
        a = Finding("n", ERROR, PROSE, 1, 0, 4, "x")
        b = Finding("n", ERROR, PROSE, 1, 0, 4, "y")
        self.assertEqual(len({a, b}), 1)

    def test_findings_come_back_in_document_order(self):
        found = scan("this page opens, and the corpus closes")
        self.assertEqual([f.name for f in found], ["page-self", "names-corpus"])


if __name__ == "__main__":
    unittest.main()
