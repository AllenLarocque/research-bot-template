#!/usr/bin/env python3
"""Inject known defects into a claim-ledger corpus, to measure what is caught.

Each operator injects exactly one defect class into exactly one row and returns
what it injected. Operators are deterministic: the same inputs always produce
the same mutation, so a detection score is reproducible and a change in it is a
real regression rather than noise.

Every operator raises MutationError rather than returning quietly when it
cannot do its job. An operator that silently does nothing produces a perfect
detection score from a harness that measured nothing, and that score is
indistinguishable from success.

The defect classes are drawn from failures that actually occurred in a research
corpus, not from imagination.
"""
import os
import re
import shutil


class MutationError(Exception):
    """An operator could not inject its defect."""


def load_corpus(src, dst):
    """Copy a corpus tree so a mutation cannot touch the original."""
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _ledger_path(root, entity):
    path = os.path.join(root, entity, "sources.md")
    if not os.path.isfile(path):
        raise MutationError(f"no ledger at {path}")
    return path


def _row_line(text, row_id):
    """(index, line) of the ledger row whose id cell is `row_id`."""
    for i, line in enumerate(text.splitlines()):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells and cells[0] == row_id:
            return i, line
    raise MutationError(f"no row with id {row_id!r}")


def _replace_row(path, row_id, transform):
    """Apply `transform` to one row's cells; leave every other byte alone."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    i, line = _row_line(text, row_id)
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    before = list(cells)
    cells = transform(cells)
    if cells == before:
        raise MutationError(f"row {row_id} unchanged — operator injected nothing")
    lines = text.splitlines(keepends=True)
    ending = "\n" if lines[i].endswith("\n") else ""
    lines[i] = "| " + " | ".join(cells) + " |" + ending
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("".join(lines))


# Deliberately generic: no snapshot in any corpus should contain this, and it
# reads like the kind of confident sentence a fabricated citation carries.
_FABRICATED = ("the board minuted the decision that October as its final act "
               "before the reorganisation")


def fabricate_quote(root, entity, row_id):
    """Replace a row's quote with text appearing in no snapshot.

    Models a quote attributed to a source that does not contain it — the
    defect that prompted this whole harness.
    """
    path = _ledger_path(root, entity)

    def transform(cells):
        cells[2] = f'"{_FABRICATED}"'
        return cells

    _replace_row(path, row_id, transform)
    return _FABRICATED
