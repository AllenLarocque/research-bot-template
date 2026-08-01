#!/usr/bin/env python3
"""General-purpose web-archival tooling: fetch a URL, reduce HTML down to
plain text, and ask the Wayback Machine for an existing capture of a URL.

Extracted from mksource.py (`fetch`, `clean`) and backfill.py (`wayback`).
None of the three know anything about wikitext or source-page construction
-- `fetch` downloads bytes over HTTP, `clean` turns raw HTML into plain text
via regex + entity-unescaping, and `wayback` talks to archive.org's lookup
API and hands back a bare capture URL (or "" / None) -- so they belong in
research_core/ rather than in an adapter.

DEFAULT_UA is deliberately neutral. The original mksource.py hardcoded a
User-Agent naming the project and a personal email address, which puts both
on the wire with every outbound request from a repo that is meant to be
published; backfill.py separately hardcoded its own project-identifying
User-Agent for wayback lookups. Neither string belongs in research_core/ -- the two
adapter modules each pass their own UA explicitly via the `ua=` parameter on
every call, so the bytes those two scripts actually put on the wire are
unchanged; only the *default* a caller gets by saying nothing is different
now.
"""
import html
import json
import re
import time
import urllib.parse
import urllib.request

DEFAULT_UA = "Research bot"


def fetch(url, timeout=90, ua=None):
    """GET `url` as text, decoding as UTF-8 with lossy replacement."""
    req = urllib.request.Request(
        url, headers={"User-Agent": ua or DEFAULT_UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def clean(h):
    """Strip an HTML document down to visible text: drop <script>/<style>
    bodies, strip remaining tags, unescape entities, and collapse whitespace."""
    h = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", t)).strip()


def wayback(url, tries=4, ua=None):
    """Closest existing Wayback Machine capture of `url`.

    Returns the capture URL (possibly "" if archive.org has never captured
    it), or None if every attempt was rate-limited/failed and the caller
    should retry later.
    """
    for i in range(tries):
        try:
            req = urllib.request.Request(
                "http://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe=""),
                headers={"User-Agent": ua or DEFAULT_UA})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = resp.read().decode("utf-8", "replace")
            d = json.loads(data)  # raises if 429/HTML
            return d.get("archived_snapshots", {}).get("closest", {}).get("url", "")
        except Exception:
            time.sleep(3 + i * 3)   # backoff on 429/offline
    return None  # gave up (rate-limited)
