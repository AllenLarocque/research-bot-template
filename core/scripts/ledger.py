#!/usr/bin/env python3
"""The claim ledger: a per-entity MARKDOWN table, not wikitext.

Extracted from verify.py: `parse_ledger` reads the 8-column markdown table at
/dossiers/<Entity>/sources.md (id, claim, quote, source page, url, tier,
status, confidence), and `check_ledger_coverage` / `check_ai_verified` reason
about the parsed rows and already-parsed relationship dicts (predicate,
object, sources, verification). None of the three ever touch wikitext syntax
-- the ledger is markdown, and the relationship dicts arrive pre-parsed from
adapters.mediawiki.verify.parse_relationships -- so they belong in core/.

Everything that reads citation/reference/relationship template markup or
rendered HTML (extract_cites, parse_relationships, check_ref_markup,
missing_templates, check_render, verify_entity, main) stays in
adapters/mediawiki/verify.py.
"""

EMPTY_QUOTE = ("", "—", "-", "–", "n/a", "N/A")


def parse_ledger(md):
    """Parse the 8-column claim ledger out of /dossiers/<Entity>/sources.md."""
    rows = []
    for ln in md.splitlines():
        if not ln.strip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if cells[:1] == ["id"]:
            continue
        joined = "".join(cells)
        if joined and set(joined) <= set("-: "):   # markdown separator row
            continue
        if len(cells) >= 7:
            rows.append({"id": cells[0], "claim": cells[1], "quote": cells[2],
                         "source": cells[3], "url": cells[4], "tier": cells[5],
                         "status": cells[6]})
    return rows


def check_ledger_coverage(cited, ledger):
    """Every cited Source has a ledger row; every 'sourced' row has a verbatim quote."""
    errs = []
    sources = {r["source"] for r in ledger}
    for c in sorted(cited):
        if c not in sources:
            errs.append("cited Source '%s' has no ledger row" % c)
    for r in ledger:
        if r["status"] == "sourced" and r["quote"].strip() in EMPTY_QUOTE:
            errs.append("ledger claim '%s' is 'sourced' but has no verbatim quote"
                        % r["claim"][:40])
    return errs


def check_ai_verified(rels):
    """ai-verified requires 2+ sources (independence is a human/source-vetting call).

    `rels` is a list of already-parsed relationship dicts (predicate, object,
    sources, verification) -- see adapters.mediawiki.verify.parse_relationships,
    which turns relationship template markup into this shape before calling here.
    """
    errs = []
    for r in rels:
        if r["verification"] == "ai-verified" and len(r["sources"]) < 2:
            errs.append("ai-verified relationship %s → %s cites %d source(s); "
                        "needs 2+ independent T1/T2"
                        % (r["predicate"], r["object"], len(r["sources"])))
    return errs
