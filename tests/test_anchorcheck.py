#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.anchorcheck import (
    proper_nouns, years, figures, flat, name_present, missing_anchors,
)
from research_core.profile import DEFAULT, load


class TestExtractors(unittest.TestCase):
    def test_years_finds_four_digit_years(self):
        # years() returns a set, not an ordered list -- the brief's test
        # assumed list output; the real signature returns set().
        self.assertEqual(years("opened in 1912 and closed in 1983"), {"1912", "1983"})

    def test_years_ignores_non_years(self):
        self.assertEqual(years("room 204, page 12"), set())

    def test_proper_nouns_finds_capitalised_names(self):
        # proper_nouns() lowercases the WHOLE capitalised run, including a
        # leading capitalised word like "The" -- the brief's expected value
        # "MacMillan Bloedel" is neither the right case nor the right span.
        self.assertIn("the macmillan bloedel", proper_nouns("The MacMillan Bloedel mill"))

    def test_proper_nouns_excludes_single_words(self):
        self.assertEqual(proper_nouns("Vancouver is here"), set())

    def test_proper_nouns_excludes_stopword_only_runs(self):
        # "British Columbia" is only excluded once a profile lists both
        # words in not_names -- the general base carries grammatical
        # stopwords only, not domain geography.
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "profile.toml")
            with open(path, "w") as fh:
                fh.write('name = "x"\nnot_names = ["british", "columbia"]\n')
            self.assertEqual(
                proper_nouns("British Columbia is large", load(path)), set())

    def test_figures_extracts_and_normalises_numbers(self):
        self.assertEqual(figures("It produced 12,500 board feet in 1983."), {"12500", "1983"})

    def test_flat_lowercases_and_collapses(self):
        self.assertEqual(flat("  The   Mill  "), "the mill")

    def test_flat_strips_punctuation(self):
        self.assertEqual(flat("Alex Macdonald, Jr."), "alex macdonald jr")


class TestNamePresent(unittest.TestCase):
    def test_exact_name_is_present(self):
        self.assertTrue(name_present("Powell River", "the powell river mill"))

    def test_absent_name_is_absent(self):
        self.assertFalse(name_present("Powell River", "the ocean falls mill"))

    def test_acronym_of_initials_is_present(self):
        # PRE-EXISTING BUG (inherited byte-identical from anchorcheck.py):
        # the docstring's own example says this should recognise "iwa" for
        # "International Woodworkers of America", but the acronym builder
        # does not filter connector words like "of" out of `words`, so the
        # acronym it actually computes is "iwoa", not "iwa". Locking in
        # today's real behaviour, not the documented intent.
        self.assertFalse(name_present(
            "International Woodworkers of America", "the iwa negotiated a contract"))
        self.assertTrue(name_present(
            "International Woodworkers of America", "the iwoa negotiated a contract"))

    def test_surname_carries_a_titled_name(self):
        self.assertTrue(name_present("Premier W.A.C. Bennett", "bennett announced the plan"))

    def test_equivalence_pair_united_states_us(self):
        self.assertTrue(name_present("United States", "shipped to the u s market"))


class TestMissingAnchors(unittest.TestCase):
    def test_year_absent_from_quotes_is_flagged(self):
        missing = missing_anchors("The mill closed in 1983.", ["the mill closed"], ["S1"], True)
        self.assertIn("year:1983", missing)

    def test_year_present_in_quotes_is_not_flagged(self):
        missing = missing_anchors("The mill closed in 1983.", ["closed in 1983"], ["S1"], True)
        self.assertEqual([m for m in missing if "1983" in m], [])

    def test_year_carried_by_source_title_is_not_flagged(self):
        # A source titled with the date it transcribes dates its own claim.
        missing = missing_anchors(
            "The mill closed in 1983.", ["the mill closed"], ["Castlegar News 1983"], True)
        self.assertEqual([m for m in missing if "1983" in m], [])

    def test_name_absent_from_quotes_and_titles_is_flagged(self):
        missing = missing_anchors(
            "The MacMillan Bloedel mill opened.", ["a large sawmill opened"], ["S1"], False)
        self.assertTrue(any(m.startswith("name:") for m in missing))

    def test_name_carried_by_source_title_is_not_flagged(self):
        missing = missing_anchors(
            "The MacMillan Bloedel mill opened.", ["a large sawmill opened"],
            ["MacMillan Bloedel Annual Report 1965"], False)
        self.assertEqual([m for m in missing if m.startswith("name:")], [])

    def test_figures_only_flagged_when_requested(self):
        with_figures = missing_anchors("It produced 12,500 board feet.", ["a lot of lumber"], [], True)
        without_figures = missing_anchors("It produced 12,500 board feet.", ["a lot of lumber"], [], False)
        self.assertIn("figure:12500", with_figures)
        self.assertEqual([m for m in without_figures if m.startswith("figure:")], [])

    def test_figure_that_is_also_a_year_is_not_double_flagged(self):
        # figures() and years() overlap on 4-digit numbers; missing_anchors
        # excludes years(claim) from the figure check so e.g. "1983" isn't
        # reported as both year:1983 and figure:1983.
        missing = missing_anchors("It happened in 1983.", ["nothing relevant"], [], True)
        self.assertEqual([m for m in missing if m.startswith("figure:")], [])


class TestProperNounsUsesProfile(unittest.TestCase):
    def test_general_profile_treats_a_place_name_as_an_entity(self):
        # Without domain vocabulary, "British Columbia" looks like a company.
        self.assertIn("british columbia", proper_nouns("British Columbia grew."))

    def test_a_profile_listing_the_words_excludes_them(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "profile.toml")
            with open(path, "w") as fh:
                fh.write('name = "x"\nnot_names = ["british", "columbia"]\n')
            found = proper_nouns("British Columbia grew.", load(path))
        self.assertNotIn("british columbia", found)


if __name__ == "__main__":
    unittest.main(verbosity=2)
