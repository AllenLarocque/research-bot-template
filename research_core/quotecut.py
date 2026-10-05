#!/usr/bin/env python3
"""Quotations cut by position from a named capture, never retyped.

The research rulebook: a quotation is copied from the capture, never
reconstructed — extract the span by position. Every tick of the tenure
rewrite of 2026-10 carried a copy of these helpers; this is that copy as a
module. A Cutter is bound to one dossier directory; captures are named as the
ledger names them (bare, in the dossier's snapshots/, or ../<Entity>/snapshots/<f>
for a sibling's). Errors are collected, not raised, so a draft can be checked
whole. A caller in the wiki adapter turns a returned quote into a citation
with `research_mediawiki.citemarkup.format_cite(src, quote)`; this module
never sees wikitext.
"""

import html
import os
import re

MIN_QUOTE = 12


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


class Cutter:
    def __init__(self, dossier_dir):
        self.dir = dossier_dir
        self._text = {}
        self.errors = []
        self.used = []          # (source page, quote, capture)

    def path(self, cap):
        if cap.startswith('../'):
            return os.path.normpath(os.path.join(self.dir, cap))
        return os.path.normpath(os.path.join(self.dir, 'snapshots', cap))

    def text(self, cap):
        p = self.path(cap)
        if p not in self._text:
            t = open(p, encoding='utf-8', errors='replace').read()
            if p.endswith(('.html', '.htm')):
                t = re.sub(r'(?s)<script.*?</script>|<style.*?</style>', '', t)
                t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
            self._text[p] = norm(t)
        return self._text[p]

    def span(self, cap, start, end=None, nth=0):
        """The capture's text from `start` to the end of `end`; `nth` picks a
        later occurrence of `start`. A missing start is recorded and returned
        as given so the draft still reads; a non-unique start is recorded."""
        t = self.text(cap)
        i = -1
        for _ in range(nth + 1):
            i = t.find(start, i + 1)
            if i < 0:
                self.errors.append('START NOT FOUND in %s: %r' % (cap, start))
                return start
        if end is not None and nth == 0 and t.count(start) > 1:
            self.errors.append('START NOT UNIQUE (%dx) in %s: %r; give a longer start or nth' % (t.count(start), cap, start))
        if end is None:
            return t[i:i + len(start)]
        j = t.find(end, i)
        if j < 0:
            self.errors.append('END NOT FOUND in %s: %r' % (cap, end))
            return t[i:i + len(start)]
        return t[i:j + len(end)]

    def _once(self, cap, q):
        n = self.text(cap).count(q)
        if n != 1:
            self.errors.append('%d occurrences in %s: %r' % (n, cap, q))

    def _use(self, src, q, cap):
        """Record a quote's use against its capture and return it unmarked:
        research_core never emits wikitext."""
        self.used.append((src, q, cap))
        return q

    def cite(self, src, cap, start, end=None, nth=0, parts=None):
        """The quote cut from `cap`. Raises ValueError on a quote shorter
        than MIN_QUOTE; records a quote that is not unique."""
        if parts:
            q = ' … '.join(self.span(cap, p) for p in parts)
            for p in parts:
                self._once(cap, p)
        else:
            q = self.span(cap, start, end, nth)
            self._once(cap, q)
        if len(q) < MIN_QUOTE:
            raise ValueError('quote too short (%d chars): %r' % (len(q), q))
        return self._use(src, q, cap)

    def join(self, src, cap, parts):
        """Values joined by ellipses, each part checked for presence (not
        uniqueness): the form for a register record's fields."""
        t = self.text(cap)
        for p in parts:
            if p not in t:
                self.errors.append('PART NOT FOUND in %s: %r' % (cap, p))
        return self._use(src, ' … '.join(parts), cap)
