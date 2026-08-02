#!/usr/bin/env python3
"""Tests for research_core.backfill_sidecars — recovering lost attribution.

citecheck can only be exact where a sidecar records which URL produced which
snapshot. Captures made before sidecars existed have none, so this infers what
it can from evidence already on disk.

The load-bearing rule under test: a guess never populates `url`. citecheck
indexes on meta.get("url"), so anything weaker than an observation must not
appear there, or a guess gets promoted to a fact by code that is behaving
correctly.
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.backfill_sidecars import infer, write

URL_A = "https://example.org/gazette-1911"
URL_B = "https://elsewhere.test/continental-history"

LEDGER = ("| id | claim | quote | source page | url | tier | status | conf |\n"
          "|----|-------|-------|-------------|-----|------|--------|------|\n"
          '| 1 | depot | "the depot opened in 1913" | Gazette | ' + URL_A +
          " | T2 | sourced | high |\n"
          '| 2 | works | "the works closed in 1987" | History | ' + URL_B +
          " | T2 | sourced | high |")


class InferCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.entity = os.path.join(self.dir, "Ashford_Rail_Corp")
        self.snaps = os.path.join(self.entity, "snapshots")
        os.makedirs(self.snaps)
        self.ledger(LEDGER)

    def ledger(self, text):
        with open(os.path.join(self.entity, "sources.md"), "w") as fh:
            fh.write(text)

    def snapshot(self, name, body):
        with open(os.path.join(self.snaps, name), "w") as fh:
            fh.write(body)

    def by_name(self):
        return {r["snapshot"]: r for r in infer(self.entity)}


class TestExactMatch(InferCase):
    def test_a_snapshot_naming_a_cited_url_is_exact(self):
        self.snapshot("a.html",
                      '<link rel="canonical" href="%s">'
                      "<p>the depot opened in 1913</p>" % URL_A)
        rec = self.by_name()["a.html"]
        self.assertEqual(rec["attribution"], "inferred-exact")
        self.assertEqual(rec["url"], URL_A)

    def test_exact_records_carry_no_candidate_list(self):
        self.snapshot("a.html", '<a href="%s">x</a>' % URL_A)
        self.assertNotIn("candidate_urls", self.by_name()["a.html"])

    def test_a_url_not_cited_by_this_entity_is_not_evidence(self):
        # The snapshot names a URL, but the ledger does not cite it. That is
        # not attribution — it is an outbound link.
        self.snapshot("a.html", '<a href="https://unrelated.test/x">x</a>')
        self.assertEqual(self.by_name()["a.html"]["attribution"], "unknown")


class TestWeakerEvidence(InferCase):
    def test_domain_only_match_carries_candidates_and_no_url(self):
        self.snapshot("a.html", '<a href="https://example.org/other-page">x</a>')
        rec = self.by_name()["a.html"]
        self.assertEqual(rec["attribution"], "inferred-domain")
        self.assertNotIn("url", rec)
        self.assertEqual(rec["candidate_urls"], [URL_A])

    def test_two_matching_urls_are_ambiguous(self):
        self.snapshot("a.html", '<a href="%s">x</a><a href="%s">y</a>'
                      % (URL_A, URL_B))
        rec = self.by_name()["a.html"]
        self.assertEqual(rec["attribution"], "ambiguous")
        self.assertNotIn("url", rec)
        self.assertEqual(sorted(rec["candidate_urls"]), sorted([URL_A, URL_B]))

    def test_no_evidence_at_all_is_unknown_with_an_empty_candidate_list(self):
        self.snapshot("a.html", "<p>nothing useful here</p>")
        rec = self.by_name()["a.html"]
        self.assertEqual(rec["attribution"], "unknown")
        self.assertNotIn("url", rec)
        self.assertEqual(rec["candidate_urls"], [])

    def test_two_urls_on_one_host_are_ambiguous_not_domain(self):
        # Both cited URLs share a host; a domain match cannot choose between
        # them, so claiming either would be a guess dressed as an inference.
        self.ledger(LEDGER.replace(URL_B, "https://example.org/second"))
        self.snapshot("a.html", '<a href="https://example.org/unrelated">x</a>')
        self.assertEqual(self.by_name()["a.html"]["attribution"], "ambiguous")


class TestRecordShape(InferCase):
    BODY = '<a href="%s">x</a>' % URL_A

    def test_sha256_is_of_the_snapshot_as_it_is_now(self):
        self.snapshot("a.html", self.BODY)
        self.assertEqual(self.by_name()["a.html"]["sha256"],
                         hashlib.sha256(self.BODY.encode()).hexdigest())

    def test_records_carry_no_fetched_at(self):
        # When these were captured is unknown. Inventing it would fabricate
        # provenance inside a provenance record.
        self.snapshot("a.html", self.BODY)
        self.assertNotIn("fetched_at", self.by_name()["a.html"])

    def test_backfilled_at_is_iso_8601_utc(self):
        self.snapshot("a.html", self.BODY)
        stamp = self.by_name()["a.html"]["backfilled_at"]
        self.assertRegex(stamp, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_every_record_names_its_evidence(self):
        self.snapshot("a.html", self.BODY)
        self.snapshot("b.html", "<p>nothing</p>")
        for rec in infer(self.entity):
            self.assertTrue(rec["evidence"], rec)


class TestDegradesQuietly(InferCase):
    def test_an_entity_with_no_snapshots_yields_nothing(self):
        shutil.rmtree(self.snaps)
        self.assertEqual(infer(self.entity), [])

    def test_an_entity_with_no_ledger_yields_nothing(self):
        os.remove(os.path.join(self.entity, "sources.md"))
        self.snapshot("a.html", "<p>x</p>")
        self.assertEqual(infer(self.entity), [])

    def test_existing_sidecars_are_not_treated_as_snapshots(self):
        self.snapshot("a.html", '<a href="%s">x</a>' % URL_A)
        self.snapshot("a.html.meta.json", '{"url": "%s"}' % URL_A)
        self.assertEqual([r["snapshot"] for r in infer(self.entity)], ["a.html"])


class TestWrite(InferCase):
    def setUp(self):
        super().setUp()
        self.snapshot("a.html", '<a href="%s">x</a>' % URL_A)

    def sidecar_path(self):
        return os.path.join(self.snaps, "a.html.meta.json")

    def test_writes_a_sidecar_beside_the_snapshot(self):
        counts = write(infer(self.entity), self.entity)
        self.assertEqual(counts["written"], 1)
        self.assertTrue(os.path.isfile(self.sidecar_path()))

    def test_dry_run_writes_nothing_but_still_counts(self):
        counts = write(infer(self.entity), self.entity, dry_run=True)
        self.assertEqual(counts["written"], 1)
        self.assertFalse(os.path.isfile(self.sidecar_path()))

    def test_an_existing_sidecar_is_never_overwritten(self):
        # One written at capture time is better evidence than any inference.
        # Clobbering it would downgrade the record while the coverage number
        # went up.
        original = '{"url": "https://captured.test/real", "title": "t"}'
        with open(self.sidecar_path(), "w") as fh:
            fh.write(original)
        counts = write(infer(self.entity), self.entity)
        self.assertEqual(counts, {"written": 0, "skipped_existing": 1})
        self.assertEqual(open(self.sidecar_path()).read(), original)

    def test_written_json_round_trips(self):
        write(infer(self.entity), self.entity)
        with open(self.sidecar_path()) as fh:
            self.assertEqual(json.load(fh)["url"], URL_A)

    def test_the_snapshot_key_is_not_persisted(self):
        # It names the file the sidecar sits beside; storing it invites the
        # two to disagree after a rename.
        write(infer(self.entity), self.entity)
        with open(self.sidecar_path()) as fh:
            self.assertNotIn("snapshot", json.load(fh))


if __name__ == "__main__":
    unittest.main()
