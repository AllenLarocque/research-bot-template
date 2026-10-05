#!/usr/bin/env python3
"""Tests for research_core.quotecut: quotes cut by position from a capture."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research_core.quotecut import Cutter


class CutterCase(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)
        os.makedirs(os.path.join(self.d, 'snapshots'))
        with open(os.path.join(self.d, 'snapshots', 'lic.txt'), 'w') as fh:
            fh.write('The licence  covers 95,903 hectares. The licence was granted in 1953. Clause 44 applies.')
        with open(os.path.join(self.d, 'snapshots', 'page.html'), 'w') as fh:
            fh.write('<html><body><p>Champion Paper &amp; Fibre</p><script>x()</script></body></html>')
        self.c = Cutter(self.d)

    def test_span_by_start_and_end(self):
        self.assertEqual(self.c.span('lic.txt', 'covers', 'hectares'), 'covers 95,903 hectares')

    def test_whitespace_is_collapsed(self):
        self.assertIn('licence covers', self.c.text('lic.txt'))

    def test_cite_returns_the_quote_and_records_use(self):
        q = self.c.cite('Src', 'lic.txt', 'was granted', 'in 1953')
        self.assertEqual(q, 'was granted in 1953')
        self.assertEqual(self.c.used, [('Src', 'was granted in 1953', 'lic.txt')])
        self.assertEqual(self.c.errors, [])

    def test_an_ambiguous_start_is_an_error(self):
        self.c.cite('Src', 'lic.txt', 'The licence', 'hectares')
        self.assertTrue(any('NOT UNIQUE' in e for e in self.c.errors), self.c.errors)

    def test_nth_picks_a_later_occurrence(self):
        self.assertEqual(self.c.span('lic.txt', 'The licence', 'granted', nth=1), 'The licence was granted')

    def test_a_missing_start_is_an_error_not_a_guess(self):
        got = self.c.span('lic.txt', 'nowhere')
        self.assertEqual(got, 'nowhere')
        self.assertTrue(any('START NOT FOUND' in e for e in self.c.errors))

    def test_short_quotes_are_refused(self):
        with self.assertRaises(ValueError):
            self.c.cite('Src', 'lic.txt', 'Clause 44')

    def test_join_cuts_parts_with_ellipses(self):
        q = self.c.join('Src', 'lic.txt', ['95,903 hectares', 'granted in 1953'])
        self.assertEqual(q, '95,903 hectares … granted in 1953')

    def test_html_is_stripped_and_unescaped(self):
        self.assertEqual(self.c.text('page.html'), 'Champion Paper & Fibre')

    def test_a_sibling_dossiers_capture(self):
        other = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, other)
        os.makedirs(os.path.join(other, 'snapshots'))
        with open(os.path.join(other, 'snapshots', 'o.txt'), 'w') as fh:
            fh.write('Elsewhere entirely.')
        rel = os.path.join('..', os.path.basename(other), 'snapshots', 'o.txt')
        c = Cutter(self.d)
        self.assertEqual(c.text(rel), 'Elsewhere entirely.')


if __name__ == '__main__':
    unittest.main()
