#!/usr/bin/env python3
"""Find candidate verbatim quotes for a missing anchor, across the source cache.

The anchor audit says a sentence asserts something none of its quotes carry.
The next question is always the same: does ANY source we already hold say it?
This answers that without re-fetching anything.

usage: findquote.py "<anchor or phrase>" [more terms ...]
       findquote.py --source "<Source page title>" "<anchor>"
"""
import sys
import re

from research_core.srccache import load_manifest, source_text
from research_core.textutil import split_sentences
from research_core.profile import DEFAULT


def main(profile=DEFAULT):
    args = sys.argv[1:]
    only = None
    if args and args[0] == "--source":
        only, args = args[1], args[2:]
    if not args:
        print(__doc__)
        return
    terms = [a.lower() for a in args]
    man = load_manifest()
    titles = [only] if only else sorted(man)
    hits = 0
    for title in titles:
        body = source_text(title)
        if not body:
            continue
        flat = re.sub(r"\s+", " ", body)
        for a, b in split_sentences(flat, profile):
            s = flat[a:b].strip()
            if not (25 < len(s) < 420):
                continue
            low = s.lower()
            if all(t in low for t in terms):
                hits += 1
                print("\n[%s]" % title)
                print("   %s" % s)
    print("\n%d candidate sentence(s)" % hits)


main()
