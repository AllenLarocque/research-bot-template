---
name: research
description: Use when researching, drafting, or publishing any entity page (organization, facility, place, person, event) — routes through source-vetting, claim-ledger, attribution, verification and publishing, and enforces the self-critique gate before any completion claim.
---

# research

Produce **credible, fully-attributed, hallucination-resistant** entity pages.
Every checkable on-page fact traces to a cited source; inference is visibly
marked; "done" is earned, not asserted.

## Pipeline — run in this order, per entity

| Stage | Sub-skill | Output |
|---|---|---|
| 1. Research | — | candidate sources, read not skimmed |
| 2. Vet sources | `source-vetting` | tier + independence per source |
| 3. Build the ledger | `claim-ledger` | 8-column table in `/dossiers/<Entity>/sources.md` |
| 4. Draft the page | `attribution` | prose with inline citations and inference markers |
| 5. Verify | `verification` | the verifier prints `VERIFY PASS` |
| 6. Publish | `publishing` | page live, tagged `ai-contributed` |
| 7. Post-publish | `verification` | purge, re-render, confirm edges knit |
| 8. Self-critique | this skill | the gate below, before any completion claim |

Do not reorder. In particular: **the ledger precedes the prose.** Writing prose
first and back-filling a ledger is how invented quotes get in.

`source-vetting` and `claim-ledger` are format-neutral and live as
`SKILL.md` in the correspondingly-named subdirectory of this skill
(`source-vetting/SKILL.md`, `claim-ledger/SKILL.md`).

`attribution`, `verification` and `publishing` are **MediaWiki-specific** —
they assume a wikitext target and a MediaWiki publishing surface — and live
under the adapter, not here: `research_mediawiki/attribution/SKILL.md`,
`research_mediawiki/verification/SKILL.md`,
`research_mediawiki/publishing/SKILL.md`. If your harness does not surface
sub-skills as separately invocable, **read the file directly** at the start of
that stage using the paths above. Do not run a stage from memory of what the
sub-skill says.

## The self-critique / anti-overclaim gate

Before writing any sentence containing *done, complete, exhaustive,
comprehensive, covered, finished,* or a similar claim, produce an explicit list:

- **(a)** every claim that is `unverified`, single-sourced, or `inference`;
- **(b)** every unresolved item, and every contradiction with the brief or with
  data already on the wiki;
- **(c)** what may be missing or is not yet covered.

**The words "exhaustive" and "complete" are forbidden unless that list is empty
and the emptiness is justified.** If the list is non-empty, say what is
outstanding in the same breath as what is finished.

This exists because of a specific failure on this project: coverage was declared
"essentially exhaustive" when only the flagship Meridian-Highline ownership web
had been saturated — Continental, Ashford, Bellweather, the eastern plants, the
export terminals, the coastal yards and all labour history were untouched.
Saturating the part you can see is not coverage.

## Definition of done (per entity)

- [ ] Page live, AI-contributed banner in place, every edit tagged `ai-contributed`
- [ ] the verifier prints **VERIFY PASS** for the entity
- [ ] Sources section renders; every footnote resolves to a Source page
- [ ] Every checkable fact is cited or carries an inference marker
- [ ] Every relationship row cited; `ai-verified` only with 2+ independent T1/T2
- [ ] Source pages exist for all citations, with APA `citation` + `archive_url`
      (or an explicit on-page note if no valid snapshot exists)
- [ ] Dossier complete: ledger + `snapshots/` + a line in `/dossiers/_runs.md`
- [ ] Re-fetched the rendered page; no template/Cargo errors; incoming edges knit
- [ ] Self-critique gate cleared

## Worked example — `Fairview rail plant` traced through the pipeline

**Illustrative.** The entity, its sources and the figures below are invented, to
show what each stage produces. They are not a record of a real audit.

| Stage | State |
|---|---|
| 1–2 Research + vetting | 3 sources cited (Fairview Gazette T2; Radio Fairview T2; Ashford Rail corporate T3). FG + Radio Fairview are independent → `ai-verified` defensible. |
| 3 Ledger | ❌ `sources.md` is the old free-form table, not the 8-column ledger. |
| 4 Attribution | ❌ no inline citations — the page predates the citation model. |
| 5 Verify | ❌ `VERIFY FAIL` (no citations; no ledger rows). |
| 6 Publish | ✅ shape, banner, tags, comma-free source titles all correct. |
| 7 Post-publish | ✅ renders clean; Relationships + Timeline present; edges knit. |
| 8 Self-critique | The honest statement: *"the operational layer is complete; the attribution layer is not, and this page would not pass verification today."* |

Every stage maps to a sub-skill and every done-item is checkable. The example is
deliberately a page that **fails** — it shows the gate working rather than a
page chosen to look good.

## Retrofit backlog

Pages drafted before a skill set exists will not meet it. Plan a retrofit pass:
re-run `verify_entity` and `check_render` over the whole corpus, record standing
state in a run log, and keep the reasoning behind each correction where a later
reader can find it.

## The failure mode that survives every mechanical check

A citation can be **verbatim, resolvable, ledgered — and not evidence for the
sentence it is attached to.** Three illustrative instances — invented, but each
modelled on a real defect this check has caught:

- `Right-of-Way 44` placed the corridor "within the townships of Ashford and
  Bellweather", cited to a quote naming neither.
- `Example Manufacturing Company` dated its acquisition by Acme Corporation to
  1 May 2006, cited to a Consolidated Industries release about a 2005 real-estate sale.
- `Walter Ashgrove` had him moving to Fairview in 1959, cited to a quote about
  a depot built at Bellweather in 1970.

`scripts/anchorcheck.py` exists for this. Run it — with `weakcites.py` — before
declaring a batch done, and read what it surfaces. Roughly one flag in three has
been a real error; the rest were facts the sources carried that nobody had cited.

Two habits fall out of that experience:

- **The lead sentence is the highest-risk sentence on any page.** It summarises
  the article and collects one citation that covers a fraction of what it says.
- **Dates and superlatives are where unsourced text hides.** "renamed in 1989",
  "the second-largest employer in the region", "control passed to X in
  2006", "incorporated on 6 May" — every one of those was written by an earlier
  pass of this pipeline and none had a source.

## When sources disagree, say so on the page

Never silently pick. The corpus now carries date and figure conflicts stated in
the open — Right-of-Way 44's land grant (137,330 / 140,000 / 232,000 ha),
Meridian-Highline's acquisition of Continental (1987 / 1988), Bellweather's
incorporation (1970 / 1972), the Ashford inquiry verdict (five charges / six
offences), whether the 1967 system-wide strike won wage parity. A reader who
can see the disagreement is better served than one given false precision.
