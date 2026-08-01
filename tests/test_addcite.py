#!/usr/bin/env python3
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.addcite import insert_after


class TestInsertAfter(unittest.TestCase):
    def test_inserts_immediately_after_anchor(self):
        self.assertEqual(insert_after("The mill closed. Later, it burned.",
                                      "The mill closed.", "[C]"),
                         "The mill closed.[C] Later, it burned.")

    def test_missing_anchor_raises(self):
        # BEHAVIOUR CHANGE (sanctioned): the original addcite.py:main counted
        # occurrences (`n = wt.count(after)`) and, for n == 0, printed a
        # REFUSED message and called sys.exit(1) -- already refusing, never
        # silently inserting. insert_after preserves that refusal but raises
        # ValueError instead of printing/exiting, since a pure function can't
        # do either; the CLI decides what to print.
        with self.assertRaises(ValueError):
            insert_after("The mill closed.", "no such phrase", "[C]")

    def test_ambiguous_anchor_raises(self):
        # Same original code path as above (n > 1 also fails the `n != 1`
        # check and refuses); ValueError replaces print + sys.exit(1) here too.
        with self.assertRaises(ValueError):
            insert_after("A. A.", "A.", "[C]")

    def test_anchor_at_end_of_text(self):
        self.assertEqual(insert_after("The mill closed.", "The mill closed.", "[C]"),
                         "The mill closed.[C]")

    def test_insertion_is_verbatim_not_reparsed(self):
        # insert_after does no markup handling of its own -- the caller (the
        # wiki adapter) is responsible for building `insertion` (e.g. via
        # format_cite) before calling this. Confirms it is just string
        # surgery: whatever is passed in appears verbatim.
        self.assertEqual(
            insert_after("Anchor text here.", "Anchor text here.",
                         "<ref>{{Cite|S|quote=q}}</ref>"),
            "Anchor text here.<ref>{{Cite|S|quote=q}}</ref>",
        )

    def test_only_one_copy_of_insertion_is_added(self):
        # Guards against a naive implementation that used str.replace with an
        # unbounded count and happened to work only because n == 1 was
        # already enforced elsewhere.
        text = "Same sentence. Same sentence. Different one."
        result = insert_after(text, "Different one.", "[C]")
        self.assertEqual(result.count("[C]"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
