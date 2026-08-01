#!/usr/bin/env python3
"""Tests for research_core.webarchive: fetch/clean/wayback, extracted from
mksource.py and backfill.py.

No test performs live network I/O -- the container is firewalled and tests
must be hermetic. clean() and DEFAULT_UA are pure and tested directly.
fetch()/wayback() are covered by monkeypatching urllib.request.urlopen with
a fake response object (and time.sleep, so a forced-failure wayback() case
doesn't actually block for the real 3s+ backoff) -- this exercises the real
fetch()/wayback() code paths (header construction, decoding, JSON parsing,
retry/backoff, giving up) without ever reaching the network. The adapter's
own scripts (mksource.py, backfill.py) are the ones that make real requests,
and are exercised by integration runs, not here.
"""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research_core.webarchive import clean, fetch, wayback, DEFAULT_UA


class TestClean(unittest.TestCase):
    def test_strips_script_and_style(self):
        out = clean("<p>keep</p><script>drop()</script><style>.x{}</style>")
        self.assertNotIn("drop()", out)
        self.assertIn("keep", out)

    def test_keeps_visible_text(self):
        self.assertIn("The mill closed", clean("<div><p>The mill closed</p></div>"))


class TestDefaultUserAgent(unittest.TestCase):
    def test_default_ua_carries_no_personal_email(self):
        self.assertNotIn("@", DEFAULT_UA)

    def test_default_ua_does_not_name_the_project(self):
        self.assertNotIn("ForestWiki", DEFAULT_UA)


class _FakeResponse:
    def __init__(self, body):
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestFetchNoNetwork(unittest.TestCase):
    def test_uses_default_ua_when_none_given(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["ua"] = req.get_header("User-agent")
            return _FakeResponse("hello")

        with mock.patch("research_core.webarchive.urllib.request.urlopen", fake_urlopen):
            out = fetch("http://example.test/page")
        self.assertEqual(out, "hello")
        self.assertEqual(captured["ua"], DEFAULT_UA)

    def test_explicit_ua_overrides_default(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["ua"] = req.get_header("User-agent")
            return _FakeResponse("body")

        with mock.patch("research_core.webarchive.urllib.request.urlopen", fake_urlopen):
            fetch("http://example.test/page", ua="Custom/1.0")
        self.assertEqual(captured["ua"], "Custom/1.0")


class TestWaybackNoNetwork(unittest.TestCase):
    def test_returns_closest_capture_url(self):
        payload = json.dumps({"archived_snapshots": {"closest": {"url": "http://web.archive.org/x"}}})

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(payload)

        with mock.patch("research_core.webarchive.urllib.request.urlopen", fake_urlopen):
            out = wayback("http://example.test/page")
        self.assertEqual(out, "http://web.archive.org/x")

    def test_returns_empty_string_when_never_captured(self):
        payload = json.dumps({"archived_snapshots": {}})

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(payload)

        with mock.patch("research_core.webarchive.urllib.request.urlopen", fake_urlopen):
            out = wayback("http://example.test/page")
        self.assertEqual(out, "")

    def test_gives_up_after_tries_exhausted_without_sleeping_for_real(self):
        attempts = []

        def fake_urlopen(req, timeout=None):
            attempts.append(1)
            raise OSError("simulated network failure")

        with mock.patch("research_core.webarchive.urllib.request.urlopen", fake_urlopen), \
             mock.patch("research_core.webarchive.time.sleep") as fake_sleep:
            out = wayback("http://example.test/page", tries=3)
        self.assertIsNone(out)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(fake_sleep.call_count, 3)

    def test_default_ua_used_when_none_given(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["ua"] = req.get_header("User-agent")
            return _FakeResponse(json.dumps({"archived_snapshots": {}}))

        with mock.patch("research_core.webarchive.urllib.request.urlopen", fake_urlopen):
            wayback("http://example.test/page")
        self.assertEqual(captured["ua"], DEFAULT_UA)


if __name__ == "__main__":
    unittest.main(verbosity=2)
