#!/usr/bin/env python3
"""Flag prose that talks about the research process instead of the subject.

A page is written for a reader who arrives years from now knowing nothing about
how it was made; the dossier and the edit summary are written for a reviewer who
wants to know exactly that. When the two audiences get mixed, the reader is the
one who loses: an article announcing "this is the first source on this page that
is not Wikipedia" has stopped describing its subject and started describing its
own history, and that sentence stops being true the moment anyone adds another
source.

This module answers one question about a body of text: which spans address the
reviewer rather than the reader? It cannot decide whether a span should be
deleted or rewritten -- "the page rests on a single publisher" is process
narration while "no source found covers the mill's tenure history" is a fact
about the record, and the two look alike from here. It ranks and locates; a
human or an agent decides.

Two severities, because a check that flags everything is a check that gets
ignored. ERROR spans name the machinery -- the briefing file, the corpus, the
dossier, "this wiki" -- and are never right on a page, so they need no judgment.
WARN spans are usually narration and sometimes legitimate: "This page is about
the man" is a scope note disambiguating a father from his son, and blocking on
it would make the gate unusable on the day it shipped.

Nothing here knows what a wiki is. It takes text and returns offsets. Which
spans a reader never sees, and which surface an offset sits on, are properties
of a markup format -- callers supply both. `research_mediawiki.voicemarkup` is
the MediaWiki answer.

THE ONE THING A CALLER MUST GET RIGHT: `skip`. The response to a finding is
"reword this", so a finding inside a quotation is an instruction to fabricate,
and a finding inside a retraction is an instruction to destroy provenance. Pass
the spans that must not be touched. `scan` cannot infer them -- it cannot see
the markup that marks them -- and defaults to skipping nothing so that a caller
who has not thought about it gets a visible answer rather than a silent one.
"""
import re

ERROR = "error"
WARN = "warn"
# A severity map may rate a surface IGNORE, meaning the pattern yields nothing
# there. An ISO date is a bookkeeping stamp in a row note and ordinary content
# in a date field, and a warning a reader must dismiss every time is worse than
# silence -- so it is not a quieter finding, it is no finding.
IGNORE = None

# Surface labels this module gives meaning to. A caller may use any labels it
# likes; these are the ones a severity map can key on, and DEFAULT is required
# in every map so an unlisted surface can never leave a finding unrated.
PROSE = "prose"
HEADING = "heading"
NOTE = "note"
DEFAULT = "*"

# Shared by the two ordinal patterns below, which must stay complementary: the
# same alternation, one requiring the bookkeeping context and one forbidding it.
_ORDINAL = r"\b(?:second|third|fourth|another) (?:account|source|publisher)\b"
_BOOKKEEPING_WORDS = (r"[^.]{0,60}\b(?:found|added|here|for this|on this page"
                      r"|in the corpus|from a different)\b")
_BOOKKEEPING = r"(?=" + _BOOKKEEPING_WORDS + r")"
_NOT_BOOKKEEPING = r"(?!" + _BOOKKEEPING_WORDS + r")"

# (name, severity, pattern), matched case-insensitively.
#
# On the ERROR side the test is "could a page about its subject ever want this
# word?" -- `corpus` and `dossier` fail it, and so does any phrase naming the
# order in which sources were found. `snapshot` PASSES it: "a snapshot of the
# industry in 1953" is ordinary English, so the bare word is a WARN and only the
# directory name is an ERROR.
PATTERNS = [
    ("names-briefing", ERROR, r"\bCLAUDE\.md\b"),
    ("names-corpus", ERROR, r"\bcorpus\b"),
    ("names-dossier", ERROR, r"\bdossiers?\b|\bsnapshots?/"),
    ("names-wiki", ERROR, r"\bthis wiki\b|\bthe wiki\b"),
    # `no .. row is written` reaches the forms that omit the word
    # "relationship" -- "No row is written for Island Timberlands", "No
    # `holds_tenure` row is written" -- and `this row` reaches a page
    # discussing which rows it carries. A page has no business doing either.
    ("names-apparatus", ERROR,
     r"\brelationship rows?\b|\bSource pages?\b|\bthe audit queue\b"
     r"|\bverification counters?\b|\bthe claim ledger\b"
     r"|\bno\b[^.]{0,20}\brow is written\b|\bthis row\b"),
    # Bookkeeping announcements, which no page has a reason to make.
    #
    # The ordinal alternative carries a context requirement the others do not.
    # "publisher" was the whole alternation until pass 1 widened it to
    # account|source on 33 instances, every one an announcement -- and the
    # widening note claimed none was "a page saying something like 'a second
    # source of pulp logs'". Pass 2 found the counter-example: "a second
    # production line that Hak counts as a mill and another source would not"
    # is two writers counting differently, which is the source-disagreement
    # content the rule asks for. See `source-ordinal` for the rest of the fix.
    ("progress-note", ERROR,
     r"\bfirst source on this page\b|\balready in the corpus\b"
     r"|\bnew here\b|\bthis pass\b|\ba later pass\b"
     r"|" + _ORDINAL + _BOOKKEEPING),
    # The same ordinal WITHOUT a bookkeeping word nearby -- disjoint from the
    # pattern above by construction, so one span never counts twice.
    #
    # Requiring the context would have dropped the false positive and also
    # dropped "== A second account of the affair ==", which is always
    # narration: a section heading organised by source-order is the page
    # describing its own research, whatever words follow. Surface carries the
    # distinction the text does not, so this is an error where only an agent
    # writes -- headings and row notes -- and a question in running prose.
    ("source-ordinal", {HEADING: ERROR, NOTE: ERROR, DEFAULT: WARN},
     _ORDINAL + _NOT_BOOKKEEPING),
    # No page has a legitimate reason to name a script. Two in the corpus when
    # this was added, both tools of this project's own.
    ("names-tool", ERROR, r"\b\w+\.py\b"),
    # A row note recording the edit that made the row: the largest unflagged
    # class in the pass-2 cleanup, on twenty-odd pages, and nothing touched it.
    # A page has no reason to date its own editing, and a note that needs a real
    # date has the row's date fields -- so an ISO date on the note surface is
    # the cheapest precise rule available.
    #
    # The verbs are deliberately not matched on their own. "moved from",
    # "raised from" and "migrated" are ordinary English about the subject -- a
    # head office moves, wages are raised, workers migrate. Only a FIELD-change
    # record trips this, which means the field has to be named.
    ("edit-history", {NOTE: ERROR, DEFAULT: IGNORE},
     r"\b20\d\d-\d\d-\d\d\b"
     r"|\b(?:start|end|end date|object|predicate|precision|date_precision"
     r"|verification|this row)\b[^.]{0,30}\b(?:moved|changed|raised|replaces)\b"
     r"|\boriginal note\b"),

    # `no pages? here`, not `no page here`: the singular was flagged and deleted
    # on one page the same day the plural survived on another, one letter apart.
    ("page-self", WARN,
     r"\bthis page\b|\bthe page\b|\bthis article\b|\bthis entity\b"
     r"|\bno pages? here\b|\bon this record\b"),
    # `rests on` needs a source-word near it. On its own it is ordinary
    # English and pass 2 produced two false positives: a tenure system that
    # rests on Crown authority, and a Nation's ownership that rests on its own
    # laws. Both are about the subject. The narration this exists to catch
    # always names what the page rests on -- a publisher, a source, an account.
    ("rests-on", WARN,
     r"\brests? on\b(?=[^.]{0,40}\b(?:source|publisher|account|citation)\b)"
     r"|\bsingle publisher\b|\bone publisher\b"
     r"|\bsingle (?:tertiary )?source\b"
     # `one source` is the capitalised bookkeeping note -- "ONE SOURCE, so
     # unverified" -- which `single source` never matched.
     #
     # Not followed by "of" (a mill is one source of employment), and not by a
     # reporting verb. "one source says 1988" ATTRIBUTES a disagreement to a
     # publisher, which is the form the rule asks for; flagging it would tell
     # an agent to undo the fix. "Everything here comes from one source:" is
     # the page describing its own sourcing, and still matches.
     r"|\bone source\b(?!\s+(?:of|says|said|records|gives|dates|has|reports"
     r"|puts|calls|names|adds|notes)\b)"),
    ("search-limits", WARN,
     r"\bnothing read for\b|\bnothing captured\b"
     r"|\bno source (?:says|supports|names|gives|found)\b"),
    ("snapshot-word", WARN, r"\bsnapshots?\b"),
    ("meta-unsourced", WARN, r"\bunsourced\b"),
]

_COMPILED = [(name, sev, re.compile(pat, re.I)) for name, sev, pat in PATTERNS]


def severity_for(severity, where):
    """One finding's severity, given a pattern's rating and its surface.

    A rating is either a plain severity, or a map from surface label to
    severity carrying a DEFAULT entry. The map exists because some wordings are
    narration on one surface and ordinary English on another -- see
    `source-ordinal`.
    """
    if isinstance(severity, dict):
        return severity.get(where, severity[DEFAULT])
    return severity


class Finding(object):
    """One flagged span. A plain object rather than a tuple, for printability."""

    def __init__(self, name, severity, where, line, start, end, snippet):
        self.name = name
        self.severity = severity
        self.where = where          # caller's surface label; PROSE by default
        self.line = line
        self.start = start
        self.end = end
        self.snippet = snippet

    def __repr__(self):
        return "Finding(%s, %s, %s, line=%d, %r)" % (
            self.name, self.severity, self.where, self.line, self.snippet)

    def __eq__(self, other):
        return (isinstance(other, Finding)
                and (self.name, self.start, self.end)
                == (other.name, other.start, other.end))

    def __hash__(self):
        return hash((self.name, self.start, self.end))


def blank(text, spans):
    """`text` with each span replaced by spaces, one for one.

    Spaces rather than deletion: a finding reports where it is, and a
    delete-based mask slides every offset after the first skipped span and
    points the caller at the wrong sentence.
    """
    if not spans:
        return text
    out = list(text)
    for a, b in spans:
        for i in range(max(0, a), min(len(out), b)):
            out[i] = " "
    return "".join(out)


def _snippet(text, start, end, pad=60):
    a = max(0, start - pad)
    b = min(len(text), end + pad)
    return re.sub(r"\s+", " ", text[a:b]).strip()


def scan(text, skip=(), surface=None):
    """Every flagged span in `text`, in document order.

    `skip` is an iterable of (start, end) the reader never sees -- quotations,
    retractions, comments. See the module docstring: getting this wrong is the
    only way this check does damage.

    `surface` is an optional callable taking an offset and returning a label for
    where it sits (a heading, a template field, running prose). Defaults to
    PROSE for everything.

    Returns [] for text with nothing to flag. That is a real answer, unlike a
    corpus-wide sweep returning nothing -- see `audit`.
    """
    searchable = blank(text, list(skip))
    label = surface or (lambda offset: PROSE)
    found = []
    for name, severity, pattern in _COMPILED:
        for m in pattern.finditer(searchable):
            where = label(m.start())
            rated = severity_for(severity, where)
            if rated is IGNORE:
                continue
            found.append(Finding(
                name=name,
                severity=rated,
                where=where,
                line=text.count("\n", 0, m.start()) + 1,
                start=m.start(),
                end=m.end(),
                snippet=_snippet(text, m.start(), m.end()),
            ))
    found.sort(key=lambda f: (f.start, f.name))
    return found


def audit(pages, scanner=scan):
    """{title: text} -> {title: [Finding]}, titles with no findings omitted.

    `scanner` takes one page's text and returns its findings. The default knows
    nothing about markup, so it skips nothing; a caller with a markup format
    passes its own (see `research_mediawiki.voicemarkup.scan_page`).

    Raises on an empty mapping. A sweep that examined nothing and reported a
    clean corpus is the failure this project has already paid for once: it
    converts an unexamined corpus into one that merely looks examined. Zero
    pages fetched is a broken query far more often than it is a corpus with
    nothing in it.
    """
    if not pages:
        raise ValueError(
            "audit() got no pages: a corpus-wide check that examined nothing "
            "must fail loudly, not report clean")
    out = {}
    for title, text in pages.items():
        findings = scanner(text or "")
        if findings:
            out[title] = findings
    return out


def counts(results):
    """{severity: n} across an audit result."""
    out = {ERROR: 0, WARN: 0}
    for findings in results.values():
        for f in findings:
            out[f.severity] += 1
    return out


def worst_first(results):
    """Titles ordered by error count, then total -- what to fix first."""
    def key(title):
        findings = results[title]
        return (-sum(1 for f in findings if f.severity == ERROR),
                -len(findings), title)
    return sorted(results, key=key)
