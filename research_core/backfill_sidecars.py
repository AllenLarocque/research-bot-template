#!/usr/bin/env python3
"""Recover which URL produced a snapshot, for captures made before sidecars.

`citecheck` is exact only where a sidecar records the URL behind a snapshot.
Captures predating that mechanism have none, so this infers what the evidence
on disk supports — and refuses to assert more.

The rule everything else follows from: **a guess never populates `url`.**
`citecheck` indexes a snapshot only when `meta.get("url")` is truthy, so an
inference recorded there would be promoted to a fact by code behaving exactly
as designed. Weaker evidence is recorded under `candidate_urls`, which nothing
consumes automatically, so resolving it stays a deliberate human act.

Evidence, strongest first:

  inferred-exact   the snapshot's own content contains a URL that this
                   entity's ledger cites, and only one such URL
  inferred-domain  no URL matched, but the snapshot mentions a host on which
                   the ledger cites exactly one URL
  ambiguous        more than one cited URL (or, for a host, more than one
                   cited URL on it) matches
  unknown          neither a cited URL nor a cited host appears

`sha256` is computed now, so it attests the file's current state rather than
its state at capture — useful for detecting later tampering, and not a claim
to have witnessed the fetch. There is deliberately no `fetched_at`: when these
were captured is unknown, and inventing it would fabricate provenance inside a
provenance record.
"""
import hashlib
import html
import json
import os
import re
import sys
from datetime import datetime, timezone

from research_core.paths import DOSSIERS
from research_core.quoteaudit import SIDECAR_SUFFIX, ledger_quotes

ATTRIBUTIONS = ("inferred-exact", "inferred-domain", "ambiguous", "unknown")

_URL = re.compile(r'https?://[^\s"\'<>)\]]+')


def _host(u):
    try:
        host = u.split("//", 1)[1].split("/", 1)[0].lower()
    except IndexError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _cited_urls(entity_dir):
    ledger = os.path.join(entity_dir, "sources.md")
    if not os.path.isfile(ledger):
        return []
    with open(ledger, encoding="utf-8", errors="ignore") as fh:
        rows = ledger_quotes(fh.read())
    return sorted({r["url"] for r in rows if r["url"].startswith("http")})


def _classify(body, cited):
    """(attribution, evidence, urls) for one snapshot's raw text."""
    found = {u.rstrip("/") for u in _URL.findall(html.unescape(body))}
    exact = [c for c in cited if c.rstrip("/") in found]
    if len(exact) == 1:
        return "inferred-exact", "url-present-in-snapshot", exact
    if len(exact) > 1:
        return "ambiguous", "multiple-cited-urls-present", exact

    hosts = {_host(u) for u in found}
    on_host = [c for c in cited if _host(c) in hosts]
    if len(on_host) == 1:
        return "inferred-domain", "sole-cited-url-on-this-host", on_host
    if len(on_host) > 1:
        return "ambiguous", "multiple-cited-urls-on-matching-host", on_host
    return "unknown", "no-cited-url-or-host-found-in-snapshot", []


def infer(entity_dir):
    """One record per snapshot. Pure: reads and returns, writes nothing."""
    snapdir = os.path.join(entity_dir, "snapshots")
    cited = _cited_urls(entity_dir)
    if not cited or not os.path.isdir(snapdir):
        return []

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = []
    for name in sorted(os.listdir(snapdir)):
        path = os.path.join(snapdir, name)
        if name.endswith(SIDECAR_SUFFIX) or not os.path.isfile(path):
            continue
        with open(path, "rb") as fh:
            raw = fh.read()
        attribution, evidence, urls = _classify(
            raw.decode("utf-8", "ignore"), cited)
        rec = {"snapshot": name, "attribution": attribution,
               "evidence": evidence, "sha256": hashlib.sha256(raw).hexdigest(),
               "backfilled_at": stamp}
        if attribution == "inferred-exact":
            rec["url"] = urls[0]
        else:
            rec["candidate_urls"] = urls
        out.append(rec)
    return out


def write(records, entity_dir, dry_run=False):
    """Persist inferred records. Returns {"written", "skipped_existing"}.

    An existing sidecar is never overwritten: one written at capture time is
    stronger evidence than anything inferable afterwards, and replacing it
    would downgrade the record while the coverage count rose.
    """
    snapdir = os.path.join(entity_dir, "snapshots")
    counts = {"written": 0, "skipped_existing": 0}
    for rec in records:
        path = os.path.join(snapdir, rec["snapshot"] + SIDECAR_SUFFIX)
        if os.path.exists(path):
            counts["skipped_existing"] += 1
            continue
        counts["written"] += 1
        if dry_run:
            continue
        body = {k: v for k, v in rec.items() if k != "snapshot"}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(body, fh, indent=1, sort_keys=True)
    return counts


def summarise(root):
    """{attribution: count} across a corpus root."""
    counts = {a: 0 for a in ATTRIBUTIONS}
    for name in sorted(os.listdir(root)):
        entity_dir = os.path.join(root, name)
        if name.startswith("_") or not os.path.isdir(entity_dir):
            continue
        for rec in infer(entity_dir):
            counts[rec["attribution"]] += 1
    return counts


def main(argv=None):
    """Dry by default. Writing 166 files should be an explicit act."""
    argv = list(sys.argv[1:] if argv is None else argv)
    do_write = "--write" in argv
    args = [a for a in argv if not a.startswith("--")]
    root = args[0] if args else DOSSIERS

    total = {"written": 0, "skipped_existing": 0}
    counts = {a: 0 for a in ATTRIBUTIONS}
    for name in sorted(os.listdir(root)):
        entity_dir = os.path.join(root, name)
        if name.startswith("_") or not os.path.isdir(entity_dir):
            continue
        recs = infer(entity_dir)
        for rec in recs:
            counts[rec["attribution"]] += 1
        got = write(recs, entity_dir, dry_run=not do_write)
        for k in total:
            total[k] += got[k]

    print("corpus:", root, "" if do_write else "  (DRY RUN — pass --write)")
    for a in ATTRIBUTIONS:
        print(f"  {a:16} {counts[a]:5}")
    print(f"  {'-' * 22}")
    print(f"  {'would write' if not do_write else 'written':16} "
          f"{total['written']:5}")
    print(f"  {'kept existing':16} {total['skipped_existing']:5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
