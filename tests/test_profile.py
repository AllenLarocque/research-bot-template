#!/usr/bin/env python3
"""Tests for research_core.profile — domain vocabulary as data.

The domain layer is a TOML file, not a Python package: a second domain should
be a file rather than a fork. The merge is add-only, so a profile can extend
the general base but never remove from it.
"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.profile import DEFAULT, Profile, ProfileError, load


class ProfileCase(unittest.TestCase):
    """Writes throwaway profiles into a directory removed after each test."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)

    def write(self, body):
        path = os.path.join(self.dir, "profile.toml")
        with open(path, "w") as fh:
            fh.write(body)
        return path


class TestDefault(unittest.TestCase):
    def test_default_is_general_not_domain_specific(self):
        self.assertEqual(DEFAULT.name, "general")

    def test_default_carries_general_abbreviations(self):
        self.assertIn("Ltd.", DEFAULT.abbreviations)

    def test_default_carries_no_domain_abbreviations(self):
        self.assertNotIn("B.C.", DEFAULT.abbreviations)

    def test_default_owned_things_matches_nothing(self):
        # No domain loaded means no domain nouns; the pattern must not match
        # an arbitrary word rather than matching everything.
        self.assertIsNone(DEFAULT.owned_things.search("mill"))


class TestLoad(ProfileCase):
    def test_reads_the_profile_name(self):
        p = load(self.write('name = "bc_forestry"\n'))
        self.assertEqual(p.name, "bc_forestry")

    def test_overlay_adds_to_the_general_abbreviations(self):
        p = load(self.write('name = "x"\nabbreviations = ["B.C."]\n'))
        self.assertIn("B.C.", p.abbreviations)
        self.assertIn("Ltd.", p.abbreviations)

    def test_overlay_adds_to_the_general_not_names(self):
        p = load(self.write('name = "x"\nnot_names = ["columbia"]\n'))
        self.assertIn("columbia", p.not_names)
        self.assertIn("the", p.not_names)

    def test_overlay_adds_to_the_general_titles(self):
        p = load(self.write('name = "x"\ntitles = ["premier"]\n'))
        self.assertIn("premier", p.titles)
        self.assertIn("dr", p.titles)

    def test_owned_things_compiles_a_word_list_into_an_alternation(self):
        p = load(self.write('name = "x"\nowned_things = ["mill", "smelter"]\n'))
        self.assertTrue(p.owned_things.search("the mill closed"))
        self.assertTrue(p.owned_things.search("the smelter closed"))
        self.assertIsNone(p.owned_things.search("the office closed"))

    def test_owned_things_matches_whole_words_only(self):
        p = load(self.write('name = "x"\nowned_things = ["mill"]\n'))
        self.assertIsNone(p.owned_things.search("millwright"))

    def test_junk_patterns_extend_the_general_junk(self):
        p = load(self.write('name = "x"\njunk_patterns = ["Harbour Publ"]\n'))
        self.assertTrue(p.junk.search("Harbour Publishing"))
        self.assertTrue(p.junk.search("Privacy policy"))

    def test_junk_matching_is_case_insensitive(self):
        p = load(self.write('name = "x"\njunk_patterns = ["Harbour Publ"]\n'))
        self.assertTrue(p.junk.search("harbour publ"))

    def test_owned_things_word_with_regex_metacharacters_matches_literally(self):
        # owned_things is documented as a word LIST. A word containing a
        # regex metacharacter must still compile and must match itself
        # literally, not be interpreted as a pattern fragment.
        p = load(self.write('name = "x"\nowned_things = ["co-op", "R&D", "5(a)"]\n'))
        self.assertTrue(p.owned_things.search("the co-op closed"))
        self.assertTrue(p.owned_things.search("led by R&D"))
        self.assertTrue(p.owned_things.search("see clause 5(a) below"))

    def test_junk_patterns_still_behave_as_regex(self):
        # junk_patterns is documented as PATTERNS, unlike owned_things, and
        # must remain unescaped so a domain can still supply real regex.
        # Single-quoted (TOML literal string) so the backslash reaches
        # tomllib unescaped.
        p = load(self.write("name = \"x\"\njunk_patterns = ['Harbour \\d+']\n"))
        self.assertTrue(p.junk.search("Harbour 42"))
        self.assertFalse(p.junk.search("Harbour Publishing"))

    def test_an_absent_section_simply_adds_nothing(self):
        p = load(self.write('name = "x"\n'))
        self.assertEqual(p.abbreviations, DEFAULT.abbreviations)


class TestLoadFailsLoudly(ProfileCase):
    def test_missing_file_raises(self):
        with self.assertRaises(ProfileError):
            load("/nonexistent/profile.toml")

    def test_malformed_toml_raises(self):
        with self.assertRaises(ProfileError):
            load(self.write("name = [unclosed\n"))

    def test_missing_name_raises(self):
        with self.assertRaises(ProfileError):
            load(self.write('abbreviations = ["B.C."]\n'))

    def test_unknown_key_raises_rather_than_being_ignored(self):
        # A typo'd key that is silently dropped is a vocabulary that quietly
        # does nothing — the failure mode this whole design exists to avoid.
        with self.assertRaises(ProfileError):
            load(self.write('name = "x"\nowned_thing = ["mill"]\n'))


if __name__ == "__main__":
    unittest.main()
