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

from research_core.textutil import norm, words

_SCRIPTISH = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
_ANY_TAG = re.compile(r"<[^>]+>")

# Straight or curly quoted spans. The floor keeps stray inch-marks and
# one-word emphasis out of the audit.
_QUOTED = re.compile(r'["“]([^"“”]{10,})["”]')
# A cell that is a single quotation from its first mark to its last: the span
# between them may itself contain quotation marks. Mark-to-mark matching stops
# at the first inner one and splits one quote into fragments that verify
# against nothing.
_WHOLE_CELL_QUOTE = re.compile(r'^["“](.{10,})["”]$', re.S)
_URL = re.compile(r"https?://\S+")
# "(as #4)" / "(as #1b)" — a back-reference to another row in the same table.
_AS_REF = re.compile(r"\(as #([0-9a-z]+)\)", re.I)
_ELLIPSIS = re.compile(r"\.\.\.|…|\[\.\.\.\]")
_EMPTY = ("", "-", "—", "–", "n/a", "N/A", "(same)")

# Below this, a fragment matches almost any body by accident.
MIN_FRAGMENT = 10

_OPENING = '"“'
_CLOSING = '"”'


def despace(s):
    """Normalised text with every space removed.

    Scanned-newspaper OCR breaks words across column boundaries, rendering
    "government officials" as "government offi cials". Comparing without
    spaces is more permissive than an exact match, but a whole sentence still
    will not collide by accident — and the space-sensitive alternative reports
    text that is demonstrably present as missing.
    """
    return norm(s).replace(" ", "")


def _fragments(quote):
    """The ellipsis-separated parts of `quote` long enough to mean anything."""
    return [p for p in (despace(p) for p in _ELLIPSIS.split(quote))
            if len(p) >= MIN_FRAGMENT]


def measurable(quote):
    """Is `quote` long enough for its presence to be evidence of anything?

    Below MIN_FRAGMENT a string matches almost any body by accident, so
    verbatim() drops short fragments — and a quote with nothing left after that
    drop comes back False, which is indistinguishable from absent. It is not
    the same claim. "Huu-ay-aht" despaces to eight characters against a floor
    of ten, and was reported MISSING corpus-wide while sitting verbatim in the
    snapshot its row names.

    Callers that report a verdict must ask this first. NOSNAP already says
    "cannot be measured" for the other reason; this is the same distinction on
    the quote's side rather than the corpus's.
    """
    return bool(_fragments(quote))


def verbatim(quote, body):
    """Is every ellipsis-separated part of `quote` present in `body`?

    `body` must already be despace()d.

    False from this function means "not found as asked", which for a quote
    below the fragment floor means "could not be asked at all" — see
    measurable(), and ask it first if the answer is going to be shown to
    anyone.
    """
    parts = _fragments(quote)
    return bool(parts) and all(p in body for p in parts)



def _outer_pair_skipped(cell):
    """Did mark-to-mark matching take an inner pair and drop the cell's own?

    True only when the cell is wrapped in one style of mark and carries the
    OTHER style inside it — straight outside and curly within, or the reverse.
    That is the shape where the outer pair cannot be matched at all, because
    the character class between the marks stops at the inner one.

    Same-style inner marks deliberately do not count. An inch mark (`3/8"`) is
    a straight mark inside a straight-quoted span, and cells like
    `"… (3/8" basis)"; "… (3/8" basis)"; "…"` hold three quotations, not one.
    Treating those as nested merges three real quotes into one string that
    matches no source.
    """
    if len(cell) < 2 or cell[0] not in _OPENING or cell[-1] not in _CLOSING:
        return False
    inner = cell[1:-1]
    if cell[0] == '"':
        return "“" in inner or "”" in inner
    return '"' in inner


def _quoted_spans(cell):
    """The quotations in a ledger cell, treating inner marks correctly.

    Two shapes share a cell: several quotations separated by "/" or ";", and a
    single quotation that itself contains quotation marks. Mark-to-mark
    matching reads the second as the first and yields fragments that verify
    against nothing.

    They are told apart by their edges. Separate quotations abut their marks —
    `"a" / "b"` gives `a` and `b`. A split quotation leaves the surrounding
    prose behind, so a fragment begins or ends with a space: `The major "pull
    factor" was ...` gives `The major ` and ` was ...`. Whitespace at a
    fragment edge therefore means the cell was cut, not that it held two
    quotations.

    That edge test misses one shape: a single quotation whose inner marks wrap
    a tidy term with no surrounding space, `"… the record calls “Huu-ay-aht”,
    signed …"`. The character class cannot cross the inner mark, so the outer
    quotation is skipped and the inner TERM is audited in its place — which is
    how a quote sitting verbatim in its own snapshot came to be reported
    MISSING corpus-wide on Alberni_Pacific_Division.

    `_outer_pair_skipped` is the second entry to the same fallback, and it is
    deliberately narrow. A first attempt asked instead whether the text between
    matches was separator-only, which reads well and is wrong: quoted text
    containing an inch mark (`3/8"`) truncates every fragment, leaving real
    text between matches in cells that genuinely hold three quotations. That
    rewrite turned one false MISSING into three. Adding a condition cannot
    regress what the edge test already got right; replacing it can.
    """
    cell = cell.strip()
    parts = _QUOTED.findall(cell)
    if parts and (any(p != p.strip() for p in parts) or _outer_pair_skipped(cell)):
        whole = _WHOLE_CELL_QUOTE.match(cell)
        if whole:
            return [whole.group(1)]
    return parts


def ledger_quotes(md):
    """Every quoted span in a ledger's markdown tables.

    Yields dicts of id, quote, url, retracted. Handles both the 8-column
    ledger and the older 6-column table that superseded ledgers retain below
    them: the quote is at cell index 2 in both, but the URL column is not, so
    take the first URL-looking cell after the quote.

    Inheritance is deliberately narrow. A cell saying "(same as #1)" inherits
    the last cited URL, which is what that notation means. A **blank** cell
    inherits nothing: it means the row records no citation. An earlier version
    inherited whenever no URL was found, so a blank cell silently acquired the
    preceding row's source — a citation nobody made — and anything comparing
    that URL against the text then reported a misattribution that did not
    exist. An audit of a real corpus found 42 of 73 such reports were this.
    """
    out = []
    last_url = ""
    by_id = {}
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
        ref = _AS_REF.search(" ".join(cells[3:]))
        if found:
            url = last_url = by_id[cells[0]] = found.group(0)
        elif ref:
            # "(as #4)" cites row 4 specifically, which is often not the row
            # above. Resolving it to last_url would attribute the wrong source.
            url = by_id.get(ref.group(1), "")
        elif any(c.lower().startswith("(same") for c in cells[3:]):
            url = last_url           # the notation those tables use
        else:
            url = ""                 # no citation, not the one above
        if cells[2] in _EMPTY:
            continue
        retracted = "RETRACTED" in joined.upper()
        for quote in _quoted_spans(cells[2]):
            out.append({"id": cells[0], "quote": quote, "url": url,
                        "retracted": retracted})
    return out


def classify(quote, local, corpus):
    """LOCAL, GLOBAL, MISSING, NOSNAP or UNMEASURED for one quote.

    `local` is this dossier's despace()d snapshot text, or None when it
    captured nothing; `corpus` is every dossier's, concatenated. GLOBAL means
    the evidence exists but is filed under a different entity.

    UNMEASURED means the quote is too short to check either way — see
    measurable(). It is deliberately not MISSING: MISSING is a statement about
    the corpus, and there is nothing here to state.
    """
    if local is None:
        return "NOSNAP"
    if not measurable(quote):
        return "UNMEASURED"
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


# A sidecar describes a capture; it is not one. Reading it as snapshot content
# would let a quote verify against a file that was never fetched.
SIDECAR_SUFFIX = ".meta.json"


def snapshot_texts(entity_dir):
    """{filename: despace()d text} for one entity's snapshots.

    None when the entity captured nothing — a different finding from
    "captured something that does not contain the quote".
    """
    snapdir = os.path.join(entity_dir, "snapshots")
    if not os.path.isdir(snapdir):
        return None
    out = {}
    for root, _dirs, files in os.walk(snapdir):
        for name in sorted(files):
            if name.endswith(SIDECAR_SUFFIX):
                continue
            try:
                with open(os.path.join(root, name), encoding="utf-8",
                          errors="ignore") as fh:
                    raw = fh.read()
            except OSError:
                continue
            raw = _SCRIPTISH.sub(" ", raw)
            raw = _ANY_TAG.sub(" ", raw)
            out[name] = despace(html.unescape(raw))
    return out or None


def snapshot_text(entity_dir):
    """Despace()d text of every snapshot captured for one entity, pooled."""
    texts = snapshot_texts(entity_dir)
    return " ".join(texts[k] for k in sorted(texts)) if texts else None


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
