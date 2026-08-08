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

    def test_the_ordinal_forms_are_all_still_reached(self):
        # Pass 1 found the same announcement written as "a second account" and
        # "a THIRD SOURCE" three times more often than as "a second publisher".
        # Which of the two ordinal patterns claims a given span depends on
        # whether a bookkeeping word sits near it, and its severity then depends
        # on the surface -- but every one of these is still reached.
        for phrase in ("a second publisher", "A third account of the year",
                       "No second source found names it", "another account"):
            self.assertTrue(
                names(scan(phrase)) & {"progress-note", "source-ordinal"}, phrase)

    def test_progress_note_leaves_ordinary_counting_alone(self):
        # The widened alternation is two words, not one: "source" on its own
        # must not fire, or every page describing a river fires.
        self.assertEqual([f for f in scan("the second largest mill, and its "
                                          "source of logs") if f.severity == ERROR], [])

    def test_tool_names(self):
        self.assertIn("names-tool",
                      names(scan("a violation that predtypes.py could not see")))

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

    def test_page_self_catches_both_numbers_of_no_page_here(self):
        # One letter apart, and for one pass the plural was the difference
        # between a sentence being deleted and being left in place.
        self.assertIn("page-self", names(scan("The League has no page here")))
        self.assertIn("page-self", names(scan("Gray and Sturdy have no pages here")))

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


class TestSurfaceDependentSeverity(unittest.TestCase):
    """A pattern may be an error on one surface and a question on another.

    Pass 2 produced the first ERROR false positive: "a second production line
    that Hak counts as a mill and another source would not" is two writers
    counting differently -- the source-disagreement content CLAUDE.md asks for.
    It was reworded only because ERROR is the hard gate.

    A bookkeeping-context requirement drops that sentence, and also drops
    "== A second account of the affair ==", which is always narration: a
    section heading organised by source-order is the page describing its own
    research. Surface is the discriminator the text alone does not carry.
    """

    def test_a_bare_ordinal_in_a_heading_is_an_error(self):
        found = scan("A second account of the affair",
                     surface=lambda o: "heading")
        self.assertEqual([(f.name, f.severity) for f in found],
                         [("source-ordinal", ERROR)])

    def test_the_same_words_in_a_note_are_an_error(self):
        found = scan("A second account of the affair", surface=lambda o: "note")
        self.assertEqual([f.severity for f in found], [ERROR])

    def test_the_same_words_in_prose_are_only_a_warning(self):
        found = scan("a mill that Hak counts and another source would not")
        self.assertEqual([(f.name, f.severity) for f in found],
                         [("source-ordinal", WARN)])

    def test_prose_doing_bookkeeping_is_still_an_error(self):
        # The ordinal with a bookkeeping word after it is not a page comparing
        # two writers; it is a page reporting what the research turned up.
        for text in ("No second source found names Canadian Western Lumber",
                     "A THIRD SOURCE FROM A DIFFERENT PUBLISHER, added 2026-08-06",
                     "A second source was added and it corroborates the end date"):
            found = [f for f in scan(text) if f.severity == ERROR]
            self.assertTrue(found, text)
            self.assertEqual(found[0].name, "progress-note", text)

    def test_the_two_ordinal_patterns_never_both_fire(self):
        # Disjoint by construction: one requires the bookkeeping context, the
        # other forbids it. Two findings on one span would double-count it.
        for text in ("No second source found names it",
                     "another source would not"):
            names_hit = [f.name for f in scan(text)
                         if f.name in ("progress-note", "source-ordinal")]
            self.assertEqual(len(names_hit), 1, text)

    def test_an_unlisted_surface_falls_back_to_the_default(self):
        found = scan("A second account", surface=lambda o: "somewhere-new")
        self.assertEqual([f.severity for f in found], [WARN])


class TestRestsOnNarrowing(unittest.TestCase):
    """`rests on` is ordinary English until a source-word is nearby.

    Two false positives in pass 2, both about the subject: a tenure system
    resting on Crown authority, and a Nation's ownership resting on its own
    laws.
    """

    def test_ordinary_english_is_not_flagged(self):
        for text in ("it is that authority the tenure system rests on.",
                     "its ownership of land rests on the laws of hahuuli"):
            self.assertNotIn("rests-on", names(scan(text)), text)

    def test_narration_is_still_flagged(self):
        for text in ("The closure year on this page still rests on a single publisher.",
                     "Everything above rests on a single tertiary source",
                     "this row rests on one publisher and no other"):
            self.assertIn("rests-on", names(scan(text)), text)


class TestEditHistory(unittest.TestCase):
    """A row note recording the edit that made the row.

    The largest unflagged class in pass 2 -- twenty-odd pages -- and no pattern
    touched it: "PRECISION RAISED FROM circa TO year AND THE ROW VERIFIED,
    2026-08-06", "START MOVED FROM 1954-12 TO 1959", "Migrated 2026-08-05".
    A page has no reason to date its own editing; a note that needs a real date
    has the row's date fields.
    """

    def test_an_iso_date_in_a_note_is_an_error(self):
        # Two spans match here -- the field-change record and the date stamp --
        # and both are the same defect.
        found = [f for f in scan("PRECISION RAISED FROM circa TO year, 2026-08-06",
                                 surface=lambda o: "note")
                 if f.name == "edit-history"]
        self.assertEqual(len(found), 2)
        self.assertEqual(set(f.severity for f in found), {ERROR})

    def test_the_same_date_in_prose_is_not_a_finding_at_all(self):
        # Not a warning -- nothing. An ISO date in running prose or a template
        # date field is ordinary content, and a warning a reader must dismiss
        # every time is worse than silence.
        self.assertNotIn("edit-history", names(scan("signed on 2026-08-06")))

    def test_a_field_change_record_is_an_error_in_a_note(self):
        for text in ("START MOVED FROM 1954-12 TO 1959",
                     "OBJECT CHANGED FROM Port Alberni TO Vancouver",
                     "END DATE MOVED FROM 1989 TO CIRCA 1987",
                     "ORIGINAL NOTE, RETAINED"):
            found = [f for f in scan(text, surface=lambda o: "note")
                     if f.name == "edit-history"]
            self.assertTrue(found, text)

    def test_ordinary_prose_using_those_verbs_is_left_alone(self):
        # "moved from", "raised from" and "migrated" are all ordinary English
        # about the subject. Only a field-change record trips this.
        for text in ("the head office moved from Vancouver to Nanaimo in 1953",
                     "wages were raised from $1.10 to $1.35 an hour",
                     "many workers migrated from the prairies"):
            found = [f for f in scan(text, surface=lambda o: "note")
                     if f.name == "edit-history"]
            self.assertEqual(found, [], text)


class TestOneSource(unittest.TestCase):
    """`ONE SOURCE` in capitals, which `single source` never matched."""

    def test_one_source_bookkeeping_is_flagged(self):
        for text in ("ONE SOURCE, so unverified", "ONE SOURCE ONLY",
                     "One source, so unverified"):
            self.assertIn("rests-on", names(scan(text)), text)

    def test_one_source_of_something_is_left_alone(self):
        # The noun phrase, not the bookkeeping note.
        self.assertNotIn("rests-on",
                         names(scan("the mill was one source of employment")))

    def test_attributing_a_claim_to_one_source_is_left_alone(self):
        # "A disagreement between sources is content -- attribute it and move
        # on" is what the rule ASKS for. "one source says 1988" is that form,
        # and flagging it tells an agent to undo the fix.
        for text in ("acquired by Fletcher Challenge (1987; one source says 1988)",
                     "At Ocean Falls one source records both the mill and the town",
                     "one source dates the closure to 2009"):
            self.assertNotIn("rests-on", names(scan(text)), text)

    def test_the_page_describing_its_own_sourcing_is_still_flagged(self):
        for text in ("Everything here comes from one source: Parnaby's thesis",
                     "ONE SOURCE, so unverified"):
            self.assertIn("rests-on", names(scan(text)), text)


class TestRowApparatus(unittest.TestCase):
    """`No row is written` without the word "relationship"."""

    def test_no_row_is_written(self):
        for text in ("No row is written for Island Timberlands",
                     "No `holds_tenure` row is written here",
                     "No occurred_at ROW is written"):
            self.assertIn("names-apparatus", names(scan(text)), text)

    def test_a_page_naming_this_row(self):
        self.assertIn("names-apparatus", names(scan("this row records the sale")))


class TestSurfaceStraddle(unittest.TestCase):
    """A match that begins on one surface and ends on another.

    Pass 3 found the check reporting a page as clean while it carried an
    edit-history note, and this is why: scan rated a finding by the surface its
    match STARTED on. edit-history is IGNORE outside a note, so a match opening
    one character before the note marker was dropped -- and because finditer
    returns non-overlapping matches, the dropped match also consumed the correct
    one that would have matched cleanly inside the note.
    """

    def surface(self, note_from):
        return lambda off: "note" if off >= note_from else "prose"

    def test_a_match_reaching_into_a_note_is_rated_by_the_note(self):
        text = "object=Whalen note=START MOVED FROM 1950 TO 1959."
        found = [f for f in scan(text, surface=self.surface(text.index("note=")))
                 if f.name == "edit-history"]
        self.assertEqual([f.severity for f in found], [ERROR])

    def test_the_reported_surface_is_the_one_that_earned_the_rating(self):
        text = "object=Whalen note=START MOVED FROM 1950 TO 1959."
        found = [f for f in scan(text, surface=self.surface(text.index("note=")))
                 if f.name == "edit-history"]
        self.assertEqual([f.where for f in found], ["note"])

    def test_a_match_wholly_outside_is_still_ignored(self):
        # The fix must not turn IGNORE into "flag everywhere". A date in prose
        # with no note anywhere near it stays silent.
        self.assertEqual([f for f in scan("the mill closed on 2026-08-06")
                          if f.name == "edit-history"], [])

    def test_the_strongest_surface_wins(self):
        # Straddling prose (warn) and a heading (error): the error is the
        # stronger claim and rating it by whichever end came first is arbitrary.
        # No bookkeeping word in this one, or it belongs to progress-note
        # instead and never reaches the surface-mapped pattern at all.
        text = "counted by a second publisher in 1953"
        found = [f for f in scan(text, surface=lambda off: "heading" if off > 20 else "prose")
                 if f.name == "source-ordinal"]
        self.assertEqual([f.severity for f in found], [ERROR])


class TestWhitespaceTolerance(unittest.TestCase):
    """Wikitext is hard-wrapped, so a literal space is half a pattern.

    Three absence sentences were in the corpus and page-self flagged one. The
    other two escaped on a line break alone -- "have no\npages here" and "has no
    page\nhere".
    """

    def test_a_phrase_broken_across_a_line(self):
        self.assertIn("page-self", names(scan("they have no\npages here.")))
        self.assertIn("page-self", names(scan("it has no page\nhere.")))

    def test_a_phrase_broken_by_several_spaces(self):
        self.assertIn("names-wiki", names(scan("the rest of  this   wiki")))

    def test_the_unbroken_form_still_matches(self):
        self.assertIn("page-self", names(scan("they have no pages here.")))


class TestQuantifierNotTally(unittest.TestCase):
    """`any one source` quantifies over all sources; `one source` counts this
    page's.

    The {{Inference}} template on Canfor says a sentence is a synthesis and not
    something any single source states -- the opposite of the bookkeeping the
    pattern exists to catch.
    """

    def test_any_one_source_is_not_flagged(self):
        text = ("a synthesis of the cited mill pages rather than a claim made "
                "by any one source")
        self.assertNotIn("rests-on", names(scan(text)))

    def test_the_quantifier_is_excluded_across_a_line_break(self):
        self.assertNotIn("rests-on", names(scan("a claim made by any\none source")))

    def test_the_bookkeeping_form_is_still_flagged(self):
        self.assertIn("rests-on", names(scan("ONE SOURCE, so unverified")))
        self.assertIn("rests-on",
                      names(scan("Everything here comes from one source: Parnaby")))


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
