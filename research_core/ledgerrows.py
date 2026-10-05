#!/usr/bin/env python3
"""Append dated rows to a claim ledger (the markdown table in
/dossiers/<Entity>/sources.md) without rewriting what is there.

The ledger's ids are sparse and not one ascending run, so the next id is
max + 1 over the whole file (the rule in /tools/ledgerid.py). A new block of
rows goes under a dated heading with its own header row, which is how every
tick of the tenure rewrite of 2026-10 appended its rows. Withdrawing an old
row stays the job of ledgertrim.
"""

import re

HEADER = ('| id | claim | quote | source page | url | tier | status | confidence | snapshot | archive link |\n'
          '|----|-------|-------|-------------|-----|------|--------|------------|----------|--------------|\n')


def next_id(ledger_md):
    ids = [int(m.group(1)) for m in re.finditer(r'^\| (\d+) \|', ledger_md, re.M)]
    return (max(ids) + 1) if ids else 1


def row(nid, claim, quote, source, url, snapshot, archive):
    """One ledger row; a pipe in a cell becomes a slash so the table holds."""
    cell = lambda s: str(s).replace('|', '/')
    return '| %d | %s | "%s" | %s | %s | T1 | sourced | high | %s | %s |' % (
        nid, cell(claim), cell(quote), cell(source), cell(url), cell(snapshot), cell(archive) if archive else '—')


def append_section(ledger_md, heading, rows):
    """The ledger with a dated section of rows appended; unchanged when rows is empty."""
    if not rows:
        return ledger_md
    return ledger_md.rstrip('\n') + '\n\n## ' + heading + '\n\n' + HEADER + '\n'.join(rows) + '\n'
