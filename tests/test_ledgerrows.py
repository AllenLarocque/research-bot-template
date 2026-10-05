#!/usr/bin/env python3
"""Tests for research_core.ledgerrows: appending dated rows to a ledger."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research_core import ledgerrows

LEDGER = ('# Sources\n\n| id | claim | quote | source page | url | tier | status | confidence | snapshot | archive link |\n'
          '|----|-------|-------|-------------|-----|------|--------|------------|----------|--------------|\n'
          '| 7 | A claim. | "a quote" | Src | http://x | T1 | sourced | high | a.txt | — |\n'
          '| 12 | Another. | "b" | Src | http://x | T1 | sourced | high | a.txt | — |\n')


class LedgerRowsCase(unittest.TestCase):
    def test_next_id_is_max_plus_one_over_the_whole_file(self):
        self.assertEqual(ledgerrows.next_id(LEDGER), 13)

    def test_next_id_on_an_empty_ledger(self):
        self.assertEqual(ledgerrows.next_id('# Sources\n'), 1)

    def test_row_escapes_pipes_and_quotes_the_quote(self):
        r = ledgerrows.row(13, 'It | held.', 'held "it"', 'Src', 'http://u', 'cap.txt', None)
        self.assertEqual(r, '| 13 | It / held. | "held "it"" | Src | http://u | T1 | sourced | high | cap.txt | — |')

    def test_append_section_adds_a_dated_heading_and_the_rows(self):
        out = ledgerrows.append_section(LEDGER, '2026-10-04 — rows for the schema rewrite',
                                        [ledgerrows.row(13, 'c', 'q', 'Src', 'u', 's', 'a')])
        self.assertTrue(out.endswith('| 13 | c | "q" | Src | u | T1 | sourced | high | s | a |\n'))
        self.assertIn('\n## 2026-10-04 — rows for the schema rewrite\n', out)
        self.assertIn('| id | claim | quote |', out.split('## 2026-10-04')[1])

    def test_append_nothing_changes_nothing(self):
        self.assertEqual(ledgerrows.append_section(LEDGER, 'x', []), LEDGER)


if __name__ == '__main__':
    unittest.main()
