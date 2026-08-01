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


def paraphrase_quote(root, entity, row_id):
    """Reverse the quote's word order, keeping every word.

    Models a paraphrase presented inside quotation marks: the content is
    genuinely in the source, the sentence is not. Reversal is crude but it is
    deterministic and it guarantees the property that matters — every content
    word present, the contiguous string absent.
    """
    path = _ledger_path(root, entity)
    captured = {}

    def transform(cells):
        quoted = re.findall(r'"([^"]+)"', cells[2])
        if not quoted:
            raise MutationError(f"row {row_id} has no quoted span to paraphrase")
        words = quoted[0].split()
        if len(words) < 4:
            raise MutationError(f"row {row_id}'s quote is too short to reorder")
        captured["text"] = " ".join(reversed(words))
        cells[2] = f'"{captured["text"]}"'
        return cells

    _replace_row(path, row_id, transform)
    return captured["text"]


def swap_citation(root, entity, row_id, other_entity):
    """Repoint a row at a source belonging to a different entity.

    Models a claim cited to a source that does not support it — the recurring
    shape where a purchase is cited to a quote about a sale. The quote itself
    stays real, so verbatim checking cannot see this one.
    """
    donor = _ledger_path(root, other_entity)
    with open(donor, encoding="utf-8") as fh:
        donor_text = fh.read()
    _, donor_line = _row_line(donor_text, "1")
    donor_cells = [c.strip() for c in donor_line.strip().strip("|").split("|")]
    source, url = donor_cells[3], donor_cells[4]

    def transform(cells):
        cells[3], cells[4] = source, url
        return cells

    _replace_row(_ledger_path(root, entity), row_id, transform)
    return source


_YEAR = re.compile(r"\b(1[6-9]\d{2}|20\d{2})\b")


def shift_date(root, entity, row_id, delta=11):
    """Move the claim's year without moving its quote's.

    Models a dated event resting on a quote about a different year. `delta`
    defaults to 11 so the shifted year cannot be mistaken for a typo or a
    fiscal-year offset.
    """
    path = _ledger_path(root, entity)
    captured = {}

    def transform(cells):
        found = _YEAR.search(cells[1])
        if not found:
            raise MutationError(f"row {row_id}'s claim carries no year to shift")
        old = found.group(1)
        new = str(int(old) + delta)
        captured["years"] = (old, new)
        cells[1] = cells[1].replace(old, new)
        return cells

    _replace_row(path, row_id, transform)
    return captured["years"]


def strip_anchor(root, entity, row_id, name="Bellweather Junction Trust"):
    """Add an entity to the claim that none of its quotes names.

    Models the most recurrent defect observed: a claim asserting a specific
    named party, cited to a quote naming nobody. Multi-word and capitalised so
    it reads as a proper noun to anchor detection.
    """
    path = _ledger_path(root, entity)

    def transform(cells):
        if name in cells[1]:
            raise MutationError(f"row {row_id} already names {name}")
        cells[1] = f"{cells[1]}, in partnership with {name}"
        return cells

    _replace_row(path, row_id, transform)
    return name
