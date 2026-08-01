#!/usr/bin/env python3
"""research_core/ must not know what a wiki is.

Matches on wikitext SYNTAX, not on the words "mediawiki"/"wikitext". An earlier
measurement of this codebase grepped for those words and undercounted the real
coupling by roughly tenfold, because wikitext coupling looks like {{Cite|...}}
and |founded_date=, which never mention MediaWiki by name.

This is the standalone-repo reduction of the original test_layering.py. The
original also asserted two import-direction invariants (research_core/ never
imports research_mediawiki, and never imports an adapter module by bare
name) -- those made sense when both packages lived in one checkout, but
research_mediawiki/ no longer exists on disk here: the template repo was
split from the deployable by history-filtering research_core/ out on its
own. An import-direction check against a package that structurally cannot be
present is not a weaker check, it's a vacuous one, so those two tests were
deleted rather than kept-but-broken. The wikitext-syntax scan below is
unchanged and still means exactly what it meant before the split.
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "research_core")

# Wikitext as a data format, plus the project name. Each is a syntax marker that
# cannot appear in code (or docs/data) that is genuinely wiki-agnostic.
#
# Every pattern here was checked against the current contents of research_core/
# for false positives (see the review that added this comment): none of these
# fire on research_core/'s existing .py or .md files except where they caught a
# real leak (research_core/references/apa.md's wikitext italics, since reworded).
FORBIDDEN = [
    (re.compile(r"\{\{"), "template call {{...}}"),
    (re.compile(r"<ref\b"), "<ref> tag"),
    # "<references" is a distinct tag from "<ref" -- "references" continues
    # with a word character, so `<ref\b` above cannot match it; the two are
    # listed separately rather than folding one into the other.
    (re.compile(r"<references\b"), "<references> tag"),
    (re.compile(r"\[\["), "wiki link [[...]]"),
    # Not anchored to line-start, and not restricted to lowercase: a review of
    # the first version proved `TEMPLATE = "|founded_date=1900"` (mid-line),
    # `|Population2020=` (uppercase/digits) and `|founded_date =1900` (space
    # before =) all slipped through. That is the same narrow-matcher failure
    # this whole test exists to prevent. (?!=) keeps Python `==` out.
    (re.compile(r"\|\s*[A-Za-z_][A-Za-z0-9_]*\s*=(?!=)"), "infobox field |name="),
    (re.compile(r"\{\|"), "wikitext table open {|"),
    # Heading syntax: anchored to a whole line (nothing else on it) so that
    # Python's `==` equality operator -- which never appears alone bracketing
    # a line with non-"=" text on both ends -- cannot match. Requires at
    # least one non-"="/non-newline character inside so a bare "====" divider
    # (not currently used anywhere here, and not a heading) doesn't count.
    (re.compile(r"^[ \t]*==+[^=\n].*[^=\n]==+[ \t]*$", re.M), "wikitext heading ==...=="),
    # MediaWiki's redirect directive is first-thing-on-a-line. Requiring the
    # word to immediately follow "#" with no space (`\b` blocks "#REDIRECTED"
    # continuing into more letters) keeps this off the much more common
    # Python comment style `# REDIRECT ...` (space after #).
    (re.compile(r"^[ \t]*#REDIRECT\b", re.M | re.I), "#REDIRECT directive"),
    (re.compile(r"~~~~"), "wiki signature ~~~~"),
    # Wikitext italics/bold are runs of 2 or 3 apostrophes wrapping real
    # content. Guarded so an ordinary Python empty-string literal ('') can
    # never match:
    #   - `[^'\n]+` between the delimiters requires at least one character,
    #     so bare '' (nothing between two more apostrophes) never matches;
    #   - requiring a letter in that span rules out two adjacent empty
    #     strings separated only by punctuation, e.g. `x, y = '', ''`;
    #   - the lookaround guards rule out string-literal prefixes (r'', b'',
    #     f'', rb'', ...), which are the one place a word character validly
    #     abuts a quote in Python.
    (re.compile(r"forestwiki", re.I), "project name"),
]

# Apostrophe-run markup is checked in PROSE FILES ONLY, never in .py.
#
# Even well-guarded, these patterns cannot be made false-positive-free against
# Python: `'' if flag else ''` is two ordinary empty-string literals whose
# ternary keywords supply the letters the guard looks for, and it would be
# reported as "wikitext italics". A gate that fails a build over valid Python
# teaches people to distrust it, and a distrusted gate gets weakened.
#
# Scoping costs nothing real. The leak this catches was documentation --
# research_core/references/apa.md shipped `''...''` and mandated it in prose.
# Wikitext italics have no reason to appear in a .py file, and the other ten
# patterns still apply to Python.
FORBIDDEN_PROSE_ONLY = [
    (re.compile(r"(?<![A-Za-z0-9_])''[^'\n]*[A-Za-z][^'\n]*''(?![A-Za-z0-9_])"),
     "wikitext italics ''...''"),
    (re.compile(r"(?<![A-Za-z0-9_])'''[^'\n]*[A-Za-z][^'\n]*'''(?![A-Za-z0-9_])"),
     "wikitext bold '''...'''"),
]

# The one sanctioned place the project name appears in research_core/
# case-sensitively as its own identifier: research_core/paths.py's
# FORESTWIKI_* env-var fallback names (e.g. FORESTWIKI_DOSSIERS), including
# the docstring's own shorthand
# reference to the whole family ("FORESTWIKI_*" with a literal wildcard
# star). Exempts only that exact uppercase shape -- "forestwiki_dossiers" or
# "ForestWiki_Dossiers" would NOT be exempt, since env vars are conventionally
# all-caps and anything else is not the sanctioned pattern.
ENV_VAR_EXEMPT = re.compile(r"\bFORESTWIKI_(?:[A-Z_]+|\*)")

# The other sanctioned occurrence: research_core/SKILL.md's own frontmatter
# `name:` and matching H1 declare the skill PACKAGE's name, which is
# "forestwiki-research" -- a deployed identifier (the directory this skill
# is installed under, and the path segment the differential test harnesses
# and research_mediawiki/README.md's install instructions all key off of),
# not a stray mention of the wiki brand in running prose. Renaming the
# skillset itself is exactly the kind of behaviour change (ripples into
# install paths, /dossiers/_skillset/forestwiki-research/, docs) this pass
# is not authorized to make -- see the review's own "out of scope" list.
# Exempted narrowly by the exact compound identifier, not by "forestwiki"
# bare, so a real leak of the word elsewhere in research_core/ is still caught.
SKILL_NAME_EXEMPT = re.compile(r"forestwiki-research\b")


def _exempted(match, exempt_spans):
    return any(s <= match.start() and match.end() <= e for s, e in exempt_spans)


def core_files():
    """Every non-cache file under research_core/, of any type.

    Previously filtered to .py/.md, which meant a .json/.txt/.yaml dropped
    into research_core/ could carry wikitext syntax or an upward reference
    straight past the gate. Widened to any file; the wikitext-syntax test
    below reads each as text and silently skips anything that doesn't decode
    as UTF-8 (binary assets aren't a layering question this test can answer).
    """
    for dirpath, dirnames, filenames in os.walk(CORE):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if fn.endswith(".pyc"):
                continue
            yield os.path.join(dirpath, fn)


def _read_text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (UnicodeDecodeError, IsADirectoryError, PermissionError):
        return None


class TestLayering(unittest.TestCase):
    def test_core_has_no_wikitext_syntax(self):
        offences = []
        for path in core_files():
            text = _read_text(path)
            if text is None:
                continue
            exempt_spans = ([m.span() for m in ENV_VAR_EXEMPT.finditer(text)]
                            + [m.span() for m in SKILL_NAME_EXEMPT.finditer(text)])
            checks = list(FORBIDDEN)
            if not path.endswith(".py"):
                checks += FORBIDDEN_PROSE_ONLY
            for pattern, label in checks:
                for m in pattern.finditer(text):
                    if label == "project name" and _exempted(m, exempt_spans):
                        continue
                    line = text[: m.start()].count("\n") + 1
                    rel = os.path.relpath(path, ROOT)
                    offences.append("%s:%d %s" % (rel, line, label))
        self.assertEqual(offences, [],
                          "wikitext leaked into research_core/:\n  " + "\n  ".join(offences))


if __name__ == "__main__":
    unittest.main(verbosity=2)
