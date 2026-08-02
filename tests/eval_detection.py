#!/usr/bin/env python3
"""Score the checking tools against deliberately planted defects.

For each (entity, row, operator): copy the clean corpus, inject one defect, run
every detector, and record which detectors flagged THAT ROW. A detector that
flags some other row has not caught this defect — attribution is by
construction, not by matching text afterwards.

Detectors that cannot be driven from ledger data are reported n/a and never
counted, in either direction. Counting them as misses would understate
detection and defame a working tool; counting them as catches would overstate
it. Either makes the number a fiction, which is what this harness exists to
detect.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

BASELINE = os.path.join(HERE, "eval_baseline.json")

from research_core import mutate                       # noqa: E402
from research_core.anchorcheck import missing_anchors   # noqa: E402
from research_core.citecheck import attribution         # noqa: E402
from research_core.ledger import parse_ledger           # noqa: E402
from research_core.quoteaudit import audit              # noqa: E402
from research_core.weakcites import is_weak             # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures", "corpus")

# (name, callable(root, entity, row_id)). Each injects one defect class.
OPERATORS = [
    ("fabricated_quote", mutate.fabricate_quote),
    ("paraphrase_as_quote", mutate.paraphrase_quote),
    ("swapped_citation",
     lambda root, e, r: mutate.swap_citation(root, e, r, _other_entity(root, e))),
    ("shifted_date", mutate.shift_date),
    ("missing_anchor", mutate.strip_anchor),
]

# crosscheck.date_conflicts compares prose against structured infobox dates.
# A ledger row supplies a claim and a quote, not an infobox, so this harness
# cannot drive it from fixture data. Reported n/a rather than counted.
NOT_DRIVABLE = ["crosscheck.date_conflicts", "ledger.check_ledger_coverage"]


def _other_entity(root, entity):
    for name in sorted(os.listdir(root)):
        if name != entity and os.path.isdir(os.path.join(root, name)):
            return name
    raise mutate.MutationError("corpus has only one entity")


def _rows(root, entity):
    with open(os.path.join(root, entity, "sources.md"), encoding="utf-8") as fh:
        return parse_ledger(fh.read())


def _detect(root, entity, row_id):
    """Detectors that flag this specific row. Returns a list of names."""
    hits = []

    for r in audit(root):
        if r["entity"] == entity and r["id"] == row_id and r["verdict"] == "MISSING":
            hits.append("quoteaudit")

    for r in attribution(root):
        if r["entity"] == entity and r["id"] == row_id and \
                r["verdict"] == "MISATTRIBUTED":
            hits.append("citecheck")

    row = next((r for r in _rows(root, entity) if r["id"] == row_id), None)
    if row is None:
        return hits
    claim = row["claim"]
    quote = row["quote"].strip('"')

    if missing_anchors(claim, [quote], [row["source"]], False):
        hits.append("anchorcheck")
    if quote and is_weak(claim, quote):
        hits.append("weakcites")
    return hits


def run():
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "corpus")

        # False-positive control: the clean corpus must produce no findings.
        mutate.load_corpus(FIXTURES, root)
        clean = []
        for entity in sorted(os.listdir(root)):
            for row in _rows(root, entity):
                for d in _detect(root, entity, row["id"]):
                    clean.append(f"{entity}/{row['id']} flagged by {d}")
        results["_clean"] = clean

        for name, op in OPERATORS:
            cases = caught = 0
            by_detector = {}
            for entity in sorted(os.listdir(FIXTURES)):
                for row in _rows(FIXTURES, entity):
                    mutate.load_corpus(FIXTURES, root)
                    try:
                        op(root, entity, row["id"])
                    except mutate.MutationError:
                        continue        # not applicable to this row
                    cases += 1
                    hits = _detect(root, entity, row["id"])
                    if hits:
                        caught += 1
                    for h in hits:
                        by_detector[h] = by_detector.get(h, 0) + 1
            results[name] = {"cases": cases, "caught": caught,
                             "by_detector": by_detector}
    return results


def compare(res):
    """(failures, improvements) against the committed baseline."""
    with open(BASELINE, encoding="utf-8") as fh:
        base = json.load(fh)
    failures, improvements = [], []
    for name, r in res.items():
        want = base.get(name)
        if want is None:
            improvements.append(f"{name}: new class, measured "
                                f"{r['caught']}/{r['cases']} — add to baseline")
            continue
        if r["caught"] < want["caught"]:
            failures.append(f"{name}: {r['caught']}/{r['cases']}, "
                            f"baseline {want['caught']}/{want['cases']}")
        elif r["caught"] > want["caught"]:
            improvements.append(f"baseline can rise: {name} "
                                f"{want['caught']} -> {r['caught']}")
    return failures, improvements


def main():
    res = run()
    clean = res.pop("_clean")

    print("=" * 64)
    print("Detection eval — planted defects against the checking tools")
    print("=" * 64)

    if clean:
        print("\nFALSE-POSITIVE CONTROL FAILED — the clean corpus is not clean:")
        for c in clean:
            print("   ", c)
        print("\nEvery score below would be inflated by these. Fix the fixture")
        print("or the detector before reading further.")
        return 1
    print("\nclean corpus: no detector reports a finding  [OK]")

    print()
    for name, r in res.items():
        pct = (100.0 * r["caught"] / r["cases"]) if r["cases"] else 0.0
        by = ", ".join(f"{k} {v}" for k, v in sorted(r["by_detector"].items()))
        print(f"  {name:22} {r['caught']:3}/{r['cases']:<3} {pct:5.1f}%   {by}")

    print(f"\n  not driven by this harness: {', '.join(NOT_DRIVABLE)}")
    print("  (reported n/a, counted neither as catches nor as misses)")

    failures, improvements = compare(res)
    for i in improvements:
        print(f"\n  {i}")
    if failures:
        print("\nREGRESSION — a checker detects less than it used to:")
        for f in failures:
            print("   ", f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
