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

DOSSIERS = (os.environ.get("RESEARCH_DOSSIERS")
            or os.environ.get("FORESTWIKI_DOSSIERS")
            or "/dossiers")
SCRATCH = (os.environ.get("RESEARCH_SCRATCH")
           or os.environ.get("FORESTWIKI_SCRATCH")
           or "/tmp/research")
CACHE = (os.environ.get("RESEARCH_SRC_CACHE")
         or os.environ.get("FORESTWIKI_SRC_CACHE")
         or os.path.join(SCRATCH, "srccache"))


def ledger(entity):
    """Path to an entity's claim ledger."""
    return os.path.join(DOSSIERS, entity.replace(" ", "_"), "sources.md")
