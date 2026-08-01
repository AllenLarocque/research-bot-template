# research-bot-template

General-purpose research tooling for producing credible, fully-attributed,
hallucination-resistant reference-style writing: source vetting, a claim
ledger, quote/anchor auditing, cross-date checking, and a source-text
archive/cache. Nothing here knows what a wiki is — no wikitext, no
MediaWiki API calls, no publishing surface. That coupling lives one layer up,
in an adapter repo (e.g. `research-bot-mediawiki`) that imports this package
and adds the wiki-specific pieces (attribution formatting, verification
against a live wiki, publishing).

This repo is the extracted `research_core/` subtree of a larger project,
split out — with its git history intact — so the general research pipeline
can be reused by targets that are not a wiki.

## Layout

```
research_core/       the package: import it as `research_core`
  addcite.py          insert an already-formatted citation after an anchor phrase
  anchorcheck.py       flag sentences asserting an anchor none of their citations contain
  crosscheck.py        detect a date asserted in prose that disagrees with the ledger
  findquote.py          find candidate verbatim quotes for a missing anchor
  ledger.py             the claim ledger: a per-entity Markdown table, not wikitext
  paths.py               where the dossier tree and source-text cache live
  profile.py              domain vocabulary as data
  quoteaudit.py           audit claim-ledger quotes against captured snapshots
  srccache.py             read-only access to the cached source text
  textutil.py             generic text utilities (sentence splitting, word extraction, ...)
  weakcites.py             flag citations whose quote looks unlikely to support its sentence
  webarchive.py            fetch a URL, reduce HTML to text, and query the Wayback Machine
  SKILL.md                 the `research` skill definition for this pipeline
  source-vetting/SKILL.md  source-tier and independence vetting, format-neutral
  claim-ledger/SKILL.md    the claim-ledger sub-skill, format-neutral
  references/apa.md        APA citation-format reference
tests/                unittest modules, plus test_layering.py (see Coverage below)
```

## Requirements

Python 3.11, standard library only — no third-party dependencies, no
`requirements.txt`.

## Running the tests

```bash
python3 tests/run_all.py
```

`tests/test_layering.py` enforces the boundary this split depends on: no
wikitext syntax (`{{...}}`, `[[...]]`, `<ref>`, infobox `|field=`, wikitext
headings, `#REDIRECT`, wiki signatures, wikitext italics/bold, or the project
name) appears anywhere under `research_core/`. If that test fails, something
wiki-specific has leaked into the template and needs to move to the adapter
repo instead.

## Using this package

Add this repo to your `sys.path` and import `research_core`
from an adapter that supplies the wiki- or publisher-specific pieces:
source-independent vetting and ledger-building stay here; formatting
citations for a specific markup language, verifying against a live
publishing target, and pushing pages live are adapter concerns.

## Coverage

Every module has a unittest module except `findquote.py`, which arrived from the
pre-split monorepo untested and still is. That gap is inherited, not introduced
by the extraction, and is worth closing before anyone relies on it.

There is no `setup.py` or `pyproject.toml` — this is not packaged for a package
index. Put the repo on `sys.path`; there is nothing to install and no
dependencies to resolve.
