#!/usr/bin/env python3
"""Tests for research_core.staleabsence -- claims of absence that have expired.

Two sentences in the pass-2 voice cleanup asserted that something was not on the
wiki, and both were false by the time the pass reached them: Campbell River said
the 1938 fire had no page (it did), and Sayward said William P. Sayward had none
(created the same day). Both were caught incidentally, by unrelated patterns.
The handover's words: "The check found them by luck."
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.staleabsence import (
    absence_claims, candidate_names, expired,
)


def phrases(claims):
    return [c.phrase.lower() for c in claims]


class TestAbsenceClaims(unittest.TestCase):

    def test_finds_the_singular(self):
        text = "The Workers' Unity League has no page here, and none is asserted."
        self.assertEqual(phrases(absence_claims(text)), ["has no page here"])

    def test_finds_the_plural(self):
        text = "Wick Gray, David Sturdy and Judge Arthur Lord have no pages here."
        self.assertEqual(phrases(absence_claims(text)), ["have no pages here"])

    def test_finds_the_no_page_for_form(self):
        text = "There is no page for the Pacific Lime Company, which is a gap."
        self.assertEqual(phrases(absence_claims(text)), ["no page for"])

    def test_returns_the_whole_sentence_the_claim_sits_in(self):
        text = ("The mill closed in 1953. William P. Sayward has no page here. "
                "The town kept the name for another century.")
        claim, = absence_claims(text)
        self.assertIn("William P. Sayward", claim.sentence)
        self.assertNotIn("closed in 1953", claim.sentence)

    def test_ordinary_prose_makes_no_claim(self):
        text = ("The company operated three mills on the coast and a fourth at "
                "Powell River until the closure was made permanent.")
        self.assertEqual(absence_claims(text), [])

    def test_a_page_may_carry_several(self):
        text = ("Gray has no page here. The mill ran until 1953. "
                "Sturdy and Lord have no pages here.")
        self.assertEqual(len(absence_claims(text)), 2)


class TestCandidateNames(unittest.TestCase):

    def test_takes_a_capitalised_run_as_one_name(self):
        self.assertIn("William P. Sayward",
                      candidate_names("William P. Sayward has no page here."))

    def test_splits_a_list_into_separate_names(self):
        got = candidate_names(
            "Wick Gray, David Sturdy and Judge Arthur Lord have no pages here.")
        for name in ("Wick Gray", "David Sturdy", "Judge Arthur Lord"):
            self.assertIn(name, got)

    def test_offers_the_form_without_a_leading_article(self):
        # A sentence-initial "The" is capitalised like the rest of the run, but
        # the page is filed under the name, not the article.
        got = candidate_names("The Workers' Unity League has no page here.")
        self.assertIn("Workers' Unity League", got)

    def test_drops_runs_that_are_only_a_stopword(self):
        self.assertNotIn("The", candidate_names("The mill has no page here."))

    def test_a_sentence_with_no_names_yields_none(self):
        self.assertEqual(candidate_names("it has no page here."), [])


class TestExpired(unittest.TestCase):
    """The join: a claim of absence, against what actually exists now."""

    TEXT = "William P. Sayward has no page here, a red link worth following."

    def test_a_claim_whose_subject_now_exists_is_expired(self):
        got = expired({"Sayward": self.TEXT}, {"William P. Sayward"})
        self.assertEqual([(t, c.phrase.lower(), n) for t, c, n in got],
                         [("Sayward", "has no page here", ["William P. Sayward"])])

    def test_a_claim_that_is_still_true_is_not_reported(self):
        self.assertEqual(expired({"Sayward": self.TEXT}, set()), [])

    def test_extra_links_supplied_by_the_caller_are_considered(self):
        # The adapter passes wikilink targets, which core cannot parse.
        text = "The league below has no page here."
        got = expired({"P": text}, {"Workers' Unity League"},
                      extra_names=lambda title, sentence: ["Workers' Unity League"])
        self.assertEqual(len(got), 1)

    def test_the_caller_may_pre_split_the_text_into_regions(self):
        # Raw markup is not prose: sentence punctuation does not bound a
        # template parameter or a heading, so a "sentence" taken from it runs
        # across half a page and the subject of the claim is lost among
        # everything else capitalised nearby. Only the caller knows where the
        # regions are, so only the caller can cut them.
        page = "IGNORED PROSE. || Sayward has no page here. || MORE IGNORED."
        got = expired({"P": page}, {"Sayward"},
                      sentences=lambda t, text: text.split("||"))
        self.assertEqual(len(got), 1)
        self.assertNotIn("IGNORED", got[0][1].sentence)

    def test_without_regions_the_whole_text_is_one_body(self):
        page = "Sayward has no page here."
        got = expired({"P": page}, {"Sayward"})
        self.assertEqual(len(got), 1)

    def test_no_claims_anywhere_raises(self):
        # A corpus-wide sweep finding no absence claims at all is a broken
        # query far more often than a corpus that never says "no page here".
        with self.assertRaises(ValueError):
            expired({"A": "Ordinary prose about a mill and its owners."}, set())

    def test_an_empty_corpus_raises(self):
        with self.assertRaises(ValueError):
            expired({}, set())


if __name__ == "__main__":
    unittest.main()
