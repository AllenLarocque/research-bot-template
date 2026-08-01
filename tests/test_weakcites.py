#!/usr/bin/env python3
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.weakcites import anchors, words, overlap, is_weak, DEFAULT_THRESH


class TestWords(unittest.TestCase):
    def test_words_extracts_content_words(self):
        # anchors() is NOT the content-word extractor -- that's words(). The
        # brief's test conflated the two (see TestAnchors below for what
        # anchors() actually finds).
        self.assertIn("mill", words("the mill closed"))

    def test_words_drops_stopwords(self):
        self.assertNotIn("the", words("the mill closed"))

    def test_words_drops_short_tokens(self):
        # len(w) > 2 filters out two-letter tokens even when not a stopword.
        self.assertNotIn("u", words("shipped to the u s market"))


class TestOverlap(unittest.TestCase):
    def test_overlap_is_one_for_identical_text(self):
        self.assertEqual(overlap("the mill closed", "the mill closed"), 1.0)

    def test_overlap_is_zero_for_disjoint_text(self):
        self.assertEqual(overlap("the mill closed", "unrelated words here"), 0.0)

    def test_overlap_partial_overlap(self):
        # sentence content words (stopwords "the"/"in" dropped): {mill,
        # closed, 1983}. quote content words (stopwords "the"/"was"/"for"
        # dropped): {mill, closed, good}. Intersection {mill, closed} -> 2/3.
        self.assertAlmostEqual(
            overlap("the mill closed in 1983", "the mill was closed for good"),
            2 / 3,
        )

    def test_overlap_empty_quote_is_zero(self):
        self.assertEqual(overlap("the mill closed", ""), 0.0)

    def test_overlap_empty_sentence_is_zero(self):
        # sw is empty; original expression is len(sw & qw) / max(len(sw), 1)
        # so this is 0/1, not a ZeroDivisionError.
        self.assertEqual(overlap("", "the mill closed"), 0.0)

    def test_overlap_is_case_insensitive(self):
        self.assertEqual(overlap("THE MILL CLOSED", "the mill closed"), 1.0)

    def test_overlap_ignores_stopword_differences(self):
        # "the" is a stopword and does not affect the content-word overlap.
        self.assertEqual(overlap("the mill closed", "mill closed"), 1.0)

    def test_overlap_punctuation_heavy_text(self):
        self.assertEqual(
            overlap("The mill, closed!! (in 1983.)", "the mill closed in 1983"), 1.0
        )


class TestAnchors(unittest.TestCase):
    def test_anchors_extracts_years(self):
        self.assertEqual(anchors("It happened in 1983."), {"1983"})

    def test_anchors_extracts_large_numbers(self):
        self.assertEqual(anchors("It cost 12,345 dollars"), {"12,345"})

    def test_anchors_extracts_multiword_proper_nouns(self):
        self.assertIn("vancouver island", anchors("Vancouver Island is nice"))

    def test_anchors_ignores_single_capitalised_word(self):
        # The regex requires two-or-more consecutive capitalised words; a
        # lone capitalised word (even a real proper noun) does not match.
        self.assertEqual(anchors("Vancouver is nice"), set())

    def test_anchors_does_not_extract_generic_content_words(self):
        # Confirms anchors() is not a content-word extractor (see TestWords).
        self.assertEqual(anchors("the mill closed"), set())


class TestIsWeak(unittest.TestCase):
    def test_default_thresh_is_point_two(self):
        self.assertEqual(DEFAULT_THRESH, 0.20)

    def test_is_weak_true_for_low_overlap_and_no_shared_anchor(self):
        self.assertTrue(
            is_weak("the mill closed in town", "completely different words entirely")
        )

    def test_is_weak_false_when_overlap_meets_threshold(self):
        self.assertFalse(is_weak("the mill closed", "the mill closed"))

    def test_is_weak_false_when_anchor_is_shared_despite_low_overlap(self):
        # Low word overlap, but both sides carry the year 1983, so it is not
        # flagged: a shared anchor overrides low vocabulary overlap.
        self.assertFalse(
            is_weak("the mill closed in 1983", "nothing overlaps but 1983 is here")
        )

    def test_is_weak_respects_custom_threshold(self):
        # 2/3 overlap is not weak at the default 0.20 threshold, but is weak
        # against a threshold set above the observed overlap.
        sentence, quote = "the mill closed in 1983", "the mill was closed for good"
        self.assertFalse(is_weak(sentence, quote, thresh=0.20))
        self.assertTrue(is_weak(sentence, quote, thresh=0.99))


if __name__ == "__main__":
    unittest.main(verbosity=2)
