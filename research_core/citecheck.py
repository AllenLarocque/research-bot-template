#!/usr/bin/env python3
"""Is a quote cited to the source that actually carries it?

`quoteaudit` asks whether a quote is real. This asks whether it is attributed
correctly — a different question, and one nothing else in this toolset asked.
A detection eval scored the class at 0/6 before this module existed: a genuine,
verbatim quote attached to the wrong source passed every check, because
verifying that a sentence exists says nothing about where it came from.

Attribution needs a link from a cited URL to the file that captured it. Nothing
recorded that historically, and snapshots rarely carry their own canonical URL
(one in four, measured). So attribution is recorded going forward in a
`<snapshot>.meta.json` sidecar, and inferred by domain as best-effort where no
sidecar exists — with the two kept distinct in the output, because a guess
reported as a fact is the failure this whole toolset exists to prevent.

Verdicts:
  EXACT          a sidecar names the cited URL, and the quote is in that file
  MISATTRIBUTED  the quote is in some snapshot, but not the cited one
  WEAK           no sidecar; the cited domain appears in the file carrying the
                 quote — consistent, unproven
  UNRECORDED     no sidecar and no domain evidence; cannot be established

MISATTRIBUTED is the only finding. WEAK and UNRECORDED report the absence of
evidence, not the presence of a defect.

Limitations, which the verdicts are designed to make visible rather than hide:
a same-domain swap is invisible without a sidecar, since two pages on one host
are indistinguishable by domain alone; and a sidecar records what the fetcher
believed, making attribution auditable rather than certain.
"""
import json
import os
from urllib.parse import urlsplit, urlunsplit

from research_core.quoteaudit import (
    SIDECAR_SUFFIX, despace, ledger_quotes, snapshot_texts, verbatim,
)


def normalize_url(u):
    """Compare-ready URL: scheme, leading www. and a trailing slash removed.

    Query and fragment are preserved. Two URLs differing only in query string
    are different pages often enough that discarding it would mask a swap.
    """
    parts = urlsplit(u.strip())
    if not parts.netloc:
        return u.strip().rstrip("/")
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/")
    return urlunsplit(("", host, path, parts.query, parts.fragment)).lstrip("/")


def domain_of(u):
    """Host without a leading www., or "" when `u` is not a URL."""
    host = urlsplit(u.strip()).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def read_sidecar(snapshot_path):
    """The sidecar beside a snapshot, or None if absent or unreadable.

    Unreadable is treated as absent: a corrupt sidecar should degrade this
    check to its fallback, not crash a corpus-wide audit.
    """
    path = snapshot_path + SIDECAR_SUFFIX
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _recorded_urls(entity_dir, names):
    """{snapshot filename: normalized url} for those with a sidecar."""
    snapdir = os.path.join(entity_dir, "snapshots")
    out = {}
    for name in names:
        meta = read_sidecar(os.path.join(snapdir, name))
        if meta and meta.get("url"):
            out[name] = normalize_url(meta["url"])
    return out


def attribution(root):
    """One dict per quoted row: entity, id, url, verdict, snapshot."""
    rows = []
    for entity in sorted(os.listdir(root)):
        entity_dir = os.path.join(root, entity)
        ledger = os.path.join(entity_dir, "sources.md")
        if entity.startswith("_") or not os.path.isfile(ledger):
            continue
        texts = snapshot_texts(entity_dir) or {}
        recorded = _recorded_urls(entity_dir, texts)

        with open(ledger, encoding="utf-8", errors="ignore") as fh:
            for row in ledger_quotes(fh.read()):
                holders = [n for n, t in texts.items() if verbatim(row["quote"], t)]
                if not holders:
                    continue          # quoteaudit's MISSING; not ours to judge
                cited = normalize_url(row["url"])
                named = [n for n, u in recorded.items() if u == cited]
                if named:
                    hit = sorted(set(named) & set(holders))
                    verdict = "EXACT" if hit else "MISATTRIBUTED"
                    snapshot = hit[0] if hit else sorted(named)[0]
                else:
                    verdict, snapshot = _fallback(row, holders)
                rows.append({"entity": entity, "id": row["id"],
                             "url": row["url"], "verdict": verdict,
                             "snapshot": snapshot})
    return rows


def _fallback(row, holders):
    """Verdict when no sidecar names the cited URL. Filled in by Task 3."""
    return "UNRECORDED", None
