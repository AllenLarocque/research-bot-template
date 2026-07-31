#!/usr/bin/env python3
"""Audit claim-ledger quotes against the snapshots captured beside them.

A ledger row asserts that a quote is verbatim in a source. The snapshots
directory holds what was actually fetched. This module answers, per quote:
is that sentence in the captured text at all?

It exists because on 2026-07-31 a quote was found attributed to a source whose
snapshot does not contain it anywhere. The claim had already been demoted on
the page, but the invented quote stayed in the ledger — where anything
re-checking the file reads it as genuine provenance.

Nothing here knows about the wiki: a ledger is a markdown table and a snapshot
is a file of text, so this is portable to any corpus that keeps evidence beside
its claims.

A MISSING verdict is not proof of invention. It means the claim has no
provenance of record — the source may simply never have been captured. Use
`coverage` to tell "the words are all there, just not contiguous" (a paraphrase
in quotation marks) from "this content is not in the source".
"""
import html
import os
import re

from core.scripts.textutil import norm, words

_SCRIPTISH = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
_ANY_TAG = re.compile(r"<[^>]+>")

# Straight or curly quoted spans. The floor keeps stray inch-marks and
# one-word emphasis out of the audit.
_QUOTED = re.compile(r'["“]([^"“”]{10,})["”]')
_URL = re.compile(r"https?://\S+")
_ELLIPSIS = re.compile(r"\.\.\.|…|\[\.\.\.\]")
_EMPTY = ("", "-", "—", "–", "n/a", "N/A", "(same)")

# Below this, a fragment matches almost any body by accident.
MIN_FRAGMENT = 10


def despace(s):
    """Normalised text with every space removed.

    Scanned-newspaper OCR breaks words across column boundaries, rendering
    "government officials" as "government offi cials". Comparing without
    spaces is more permissive than an exact match, but a whole sentence still
    will not collide by accident — and the space-sensitive alternative reports
    text that is demonstrably present as missing.
    """
    return norm(s).replace(" ", "")


def verbatim(quote, body):
    """Is every ellipsis-separated part of `quote` present in `body`?

    `body` must already be despace()d.
    """
    parts = [despace(p) for p in _ELLIPSIS.split(quote)]
    parts = [p for p in parts if len(p) >= MIN_FRAGMENT]
    return bool(parts) and all(p in body for p in parts)


def ledger_quotes(md):
    """Every quoted span in a ledger's markdown tables.

    Yields dicts of id, quote, url, retracted. Handles both the 8-column
    ledger and the older 6-column table that superseded ledgers retain below
    them: the quote is at cell index 2 in both, but the URL column is not, so
    take the first URL-looking cell after the quote. Rows whose source cell
    says "(same)" inherit the previous row's URL, which is what that notation
    means.
    """
    out = []
    last_url = ""
    for line in md.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 5:
            continue
        joined = "".join(cells)
        if joined and set(joined) <= set("-: "):          # separator row
            continue
        if cells[0].lower() in ("id", "#"):               # header row
            continue
        found = _URL.search(" ".join(cells[3:]))
        url = found.group(0) if found else last_url
        last_url = url
        if cells[2] in _EMPTY:
            continue
        retracted = "RETRACTED" in joined.upper()
        for quote in _QUOTED.findall(cells[2]):
            out.append({"id": cells[0], "quote": quote, "url": url,
                        "retracted": retracted})
    return out


def classify(quote, local, corpus):
    """LOCAL, GLOBAL, MISSING or NOSNAP for one quote.

    `local` is this dossier's despace()d snapshot text, or None when it
    captured nothing; `corpus` is every dossier's, concatenated. GLOBAL means
    the evidence exists but is filed under a different entity.
    """
    if local is None:
        return "NOSNAP"
    if verbatim(quote, local):
        return "LOCAL"
    if verbatim(quote, corpus):
        return "GLOBAL"
    return "MISSING"


def coverage(quote, body):
    """Fraction of the quote's content words appearing anywhere in `body`.

    1.0 with a MISSING verdict means every word is in the source but not in
    that order — a paraphrase presented as a quotation. A low score means the
    content is genuinely absent, which is either invention or a truncated
    capture. `body` must already be despace()d.
    """
    content = words(quote)
    if not content:
        return 0.0
    return sum(1 for w in content if w in body) / len(content)


def snapshot_text(entity_dir):
    """Despace()d text of every snapshot captured for one entity.

    None when the entity captured nothing — which is a different finding from
    "captured something that does not contain the quote", and must not be
    collapsed into it.
    """
    snapdir = os.path.join(entity_dir, "snapshots")
    if not os.path.isdir(snapdir):
        return None
    chunks = []
    for root, _dirs, files in os.walk(snapdir):
        for name in sorted(files):
            try:
                with open(os.path.join(root, name), encoding="utf-8",
                          errors="ignore") as fh:
                    raw = fh.read()
            except OSError:
                continue
            raw = _SCRIPTISH.sub(" ", raw)
            raw = _ANY_TAG.sub(" ", raw)
            chunks.append(despace(html.unescape(raw)))
    return " ".join(chunks) if chunks else None


def audit(root):
    """Audit every entity directory under `root`.

    Returns one dict per quoted span: entity, id, quote, url, retracted,
    verdict, coverage. Directories starting with "_" are bookkeeping, not
    entities, and are skipped.
    """
    entities = {}
    snapshots = {}
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if name.startswith("_") or not os.path.isdir(d):
            continue
        ledger = os.path.join(d, "sources.md")
        if not os.path.isfile(ledger):
            continue
        with open(ledger, encoding="utf-8", errors="ignore") as fh:
            entities[name] = ledger_quotes(fh.read())
        snapshots[name] = snapshot_text(d)

    corpus = " ".join(t for t in snapshots.values() if t)

    rows = []
    for name, quotes in entities.items():
        local = snapshots.get(name)
        for row in quotes:
            rows.append(dict(row, entity=name,
                             verdict=classify(row["quote"], local, corpus),
                             coverage=coverage(row["quote"], local or "")))
    return rows
