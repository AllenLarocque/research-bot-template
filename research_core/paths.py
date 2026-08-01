#!/usr/bin/env python3
"""Where the dossier tree and the source-text cache live.

RESEARCH_DOSSIERS    dossier root holding <Entity>/sources.md   (default /dossiers)
RESEARCH_SRC_CACHE   cached source text for verbatim quote checks
RESEARCH_SCRATCH     working directory; SRC_CACHE defaults to <SCRATCH>/srccache

The FORESTWIKI_* names are honoured as fallbacks so a half-migrated checkout
keeps working.

Nothing here creates directories — a missing cache should fail loudly rather
than silently verify quotes against nothing.
"""
import os


def _env(new, old, default):
    """First of the two names actually PRESENT wins, even if set to "".

    Presence, not truthiness: the original used os.environ.get(NAME, default),
    which honours an explicitly-empty value. An `or` chain silently turns "" into
    the default, which is a behaviour change.
    """
    if new in os.environ:
        return os.environ[new]
    if old in os.environ:
        return os.environ[old]
    return default


DOSSIERS = _env("RESEARCH_DOSSIERS", "FORESTWIKI_DOSSIERS", "/dossiers")
SCRATCH = _env("RESEARCH_SCRATCH", "FORESTWIKI_SCRATCH", "/tmp/research")
# CACHE keeps truthiness (or-chain) semantics on purpose: the original already
# used os.environ.get(...) or ... here, so "" falling through to the derived
# path is the PRESERVED behaviour, not a regression.
CACHE = (os.environ.get("RESEARCH_SRC_CACHE")
         or os.environ.get("FORESTWIKI_SRC_CACHE")
         or os.path.join(SCRATCH, "srccache"))


def ledger_path(entity):
    """Path to an entity's claim ledger."""
    return os.path.join(DOSSIERS, entity.replace(" ", "_"), "sources.md")
