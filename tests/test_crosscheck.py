#!/usr/bin/env python3
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.crosscheck import date_conflicts, OPEN_FIELDS, CLOSE_FIELDS
from research_core.profile import load, DEFAULT

# The words the old profiles.bc_forestry.vocabulary.OWNED_THINGS regex
# recognised, now expressed the way a profile supplies them: as a word list
# for research_core.profile.load() to compile.
_OWNED_WORDS = ["mill", "mills", "sawmill", "plant", "operation", "operations",
                "division", "mine", "venture", "partnership", "licence",
                "license", "townsite", "town", "smelter", "line"]


def _load_profile(words):
    """Build a Profile from a word list via a real TOML file on disk."""
    d = tempfile.mkdtemp()
    try:
        path = os.path.join(d, "profile.toml")
        with open(path, "w") as fh:
            fh.write('name = "bc_forestry"\nowned_things = %s\n' % json.dumps(words))
        return load(path)
    finally:
        shutil.rmtree(d)


class TestDateConflictsTakesAProfile(unittest.TestCase):
    def test_general_profile_has_no_owned_nouns(self):
        # With no domain vocabulary, nothing is recognised as an owned thing.
        self.assertIsNone(DEFAULT.owned_things.search("mill"))

    def test_profile_owned_things_are_used(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "profile.toml")
            with open(path, "w") as fh:
                fh.write('name = "x"\nowned_things = ["mill"]\n')
            p = load(path)
        self.assertTrue(p.owned_things.search("the mill"))


class TestDateConflicts(unittest.TestCase):
    # The brief's four tests, verified against the real extracted signature
    # date_conflicts(subject, prose, years, profile=DEFAULT, window=90) --
    # held up unchanged aside from OWNED_THINGS regex -> profile object.

    @classmethod
    def setUpClass(cls):
        cls.profile = _load_profile(_OWNED_WORDS)

    def test_owned_thing_between_name_and_year_suppresses_conflict(self):
        # "MacMillan Bloedel's sawmill closed in 1983" dates the sawmill, not
        # the company. This is falsifiable against date_conflicts ignoring
        # the passed profile: if it did, "sawmill" would never suppress the
        # match and this would fail.
        out = date_conflicts("MacMillan Bloedel",
                              "MacMillan Bloedel's sawmill closed in 1983.",
                              {"closed_date": "1990"}, self.profile)
        self.assertEqual(out, [])

    def test_direct_date_conflict_is_reported(self):
        out = date_conflicts("MacMillan Bloedel",
                              "MacMillan Bloedel closed in 1983.",
                              {"closed_date": "1990"}, self.profile)
        self.assertNotEqual(out, [])

    def test_pronoun_between_name_and_year_suppresses_conflict(self):
        out = date_conflicts("MacMillan Bloedel",
                              "MacMillan Bloedel bought it; it was formed in 1983.",
                              {"founded_date": "1990"}, self.profile)
        self.assertEqual(out, [])

    def test_empty_owned_things_still_works(self):
        # DEFAULT.owned_things matches nothing (no domain vocabulary loaded)
        # and so has no suppression effect -- the conflict is reported
        # exactly as if no owned_things check existed.
        out = date_conflicts("Acme", "Acme closed in 1983.", {"closed_date": "1990"}, DEFAULT)
        self.assertNotEqual(out, [])

    # Additional cases covering what the brief's four tests did not: shape of
    # the return value, multi-year segments, multiple mentions, and the
    # window parameter.

    def test_conflict_record_shape(self):
        out = date_conflicts("Acme", "Acme closed in 1983.", {"closed_date": "1990"}, self.profile)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["kind"], "close")
        self.assertEqual(out[0]["year"], "1983")
        self.assertEqual(out[0]["own"], ["1990"])
        self.assertIn("closed in 1983", out[0]["context"])

    def test_year_matching_infobox_exactly_is_not_a_conflict(self):
        out = date_conflicts("Acme", "Acme closed in 1990.", {"closed_date": "1990"}, self.profile)
        self.assertEqual(out, [])

    def test_year_matching_any_of_several_own_fields_is_not_a_conflict(self):
        # own collects every OPEN_FIELDS value present; a match against ANY
        # of them suppresses the conflict, not just the first.
        out = date_conflicts("Acme", "Acme opened in 1905.",
                              {"founded_date": "1900", "commissioned_date": "1905"}, self.profile)
        self.assertEqual(out, [])

    def test_text_with_no_years_reports_nothing(self):
        out = date_conflicts("Acme", "Acme is a company with a long history.",
                              {"closed_date": "1990"}, self.profile)
        self.assertEqual(out, [])

    def test_empty_years_reports_nothing_even_with_matching_prose(self):
        # Mirrors the original's caller-side guard (`not years[subject]`),
        # duplicated defensively inside date_conflicts itself.
        out = date_conflicts("Acme", "Acme closed in 1983.", {}, self.profile)
        self.assertEqual(out, [])

    def test_first_candidate_year_in_a_segment_wins_even_without_conflict(self):
        # The original's `break` sits outside the innermost `if own and yr
        # not in own`, at the same indent as that if -- it fires as soon as
        # ANY year in the segment has a recognised open/close word before it,
        # whether or not that year actually conflicts. A second, truly
        # conflicting year later in the same segment is never reached.
        out = date_conflicts("Acme", "Acme founded in 1900 and 1920.",
                              {"founded_date": "1900"}, self.profile)
        self.assertEqual(out, [])

    def test_second_year_is_examined_when_first_has_no_event_word(self):
        # A year with no recognised open/close word before it does NOT
        # trigger the break -- scanning continues to the next year in the
        # segment.
        out = date_conflicts("Acme", "Acme mentioned near 1750 and closed in 1983.",
                              {"closed_date": "1990"}, self.profile)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["year"], "1983")

    def test_multiple_mentions_of_subject_each_checked_independently(self):
        out = date_conflicts("Acme", "Acme closed in 1983. Later, Acme closed in 1985.",
                              {"closed_date": "1990"}, self.profile)
        self.assertEqual([c["year"] for c in out], ["1983", "1985"])

    def test_window_limits_how_far_ahead_a_year_is_seen(self):
        out = date_conflicts("Acme", "Acme closed in 1983.", {"closed_date": "1990"},
                              self.profile, window=5)
        self.assertEqual(out, [])

    def test_open_and_close_fields_unchanged(self):
        # Generic date vocabulary, not domain knowledge -- kept in core as-is.
        self.assertEqual(OPEN_FIELDS, ("founded_date", "commissioned_date", "granted_date"))
        self.assertEqual(CLOSE_FIELDS, ("closed_date", "dissolved_date"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
