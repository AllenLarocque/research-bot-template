#!/usr/bin/env python3
"""Insert an already-formatted citation immediately after an anchor phrase.

Pure string surgery: given the exact page text the citation should follow
(`anchor`) and the already-built markup (`insertion` -- core never builds the
wiki citation tag itself, callers hand it a complete, formatted citation),
attach it right after the anchor.

BEHAVIOUR CHANGE from the original addcite.py:main (the one sanctioned change
in this task): the original counted the anchor's occurrences in the page text
(`n = wt.count(s["after"])`) and, for n != 1 (missing OR ambiguous), printed a
"REFUSED ... anchor appears N times" message and called sys.exit(1) --
already refusing rather than silently inserting at the wrong spot, but doing
so by tearing down the whole process from inside main's loop. A pure function
can't print or exit; insert_after raises ValueError instead, so a missing or
ambiguous anchor still can never be silently attached to the wrong sentence,
and the caller (the wiki CLI) decides what to print and whether to exit.
"""


def insert_after(text, anchor, insertion):
    """Insert `insertion` immediately after the first (and only) `anchor`.

    Raises ValueError if `anchor` does not occur in `text`, or occurs more
    than once -- mirroring the original's `n = text.count(anchor); if n != 1:
    refuse`, just as an exception instead of a print + sys.exit(1).
    """
    n = text.count(anchor)
    if n == 0:
        raise ValueError("anchor not found: %.60s" % anchor)
    if n > 1:
        raise ValueError("anchor appears %d times: %.60s" % (n, anchor))
    return text.replace(anchor, anchor + insertion, 1)
