---
name: claim-ledger
description: Use before writing any factual claim on an entity page. Maintains the claim ledger in `/dossiers/<Entity>/sources.md` that gates what may appear on-page (gate C) and that the verifier reads.
---

# Claim ledger

The anti-hallucination core. **A checkable fact may not be written on a page
until it exists as a ledger row.** The ledger is the upgraded claims table in
`/dossiers/<Entity>/sources.md`, and the verifier parses it.

## Schema (exactly 8 columns — the verifier depends on this)

```
| id | claim | quote | source page | url | tier | status | confidence |
```

- `quote` — the **verbatim** words from the source that support the claim. Not a
  paraphrase. Copy them.
- `source page` — the exact title of the corresponding Source page.
- `tier` — T1/T2/T3 from `source-vetting`.
- `status` — `sourced` | `inference` | `unknown` (below).
- `confidence` — high / medium / low.

## Gate C

- **`status=sourced`** → requires a nonempty verbatim quote that *directly*
  supports the claim. Only then may it go on-page, with an inline citation.
  If the quote requires a leap to reach the claim, it is not `sourced` — it is
  `inference`.
- **`status=inference`** → your synthesis, not stated by any source. May appear
  on-page **only** with an inference marker (carrying a `note=…` explaining
  why). Never rendered as plain sourced fact.
- **`status=unknown`** → **not written on the page at all.** Logged as a gap.
  *An empty field beats a wrong one.*

## What counts as "checkable"

Checkable (needs a row + citation): dates, names, ownership and corporate
relationships, numbers (employees, capacity, output, money), events, locations,
and any direct quotation.

Framing (exempt): connective and structural sentences that only restate facts
already cited nearby — "The mill changed hands twice in the following decade."
Framing may not introduce a new fact. If it does, it is checkable.

## Worked example

Three facts about a rail plant, and what each produces on-page:

| id | claim | quote | source page | url | tier | status | confidence |
|----|-------|-------|-------------|-----|------|--------|------------|
| 1 | Plant produced first locomotive 30 Nov 1965 | "the plant produced its first locomotive on November 30, 1965" | Fairview Gazette — Meridian-Highline Rail Plant 50 Years 2015 | https://… | T2 | sourced | high |
| 2 | Plant and the adjacent foundry shared a parts supply | — | — | — | — | inference | low |
| 3 | Plant's original construction cost | — | — | — | — | unknown | — |

On-page treatment:
1. `The plant produced its first locomotive on 30 November 1965` — followed by an
   inline citation naming the source page, with the verbatim quote "the plant
   produced its first locomotive on November 30, 1965" attached.
2. `The plant likely drew parts from the neighbouring foundry` — followed by
   an inference marker noting "both were operating on adjacent sites from 1965".
3. **Nothing.** The construction cost does not appear on the page in any form.
   It stays in the ledger as a gap for a human or a later pass to fill.

## Reminders

- Write the ledger *while* researching, not afterwards from memory — a
  reconstructed ledger is where invented quotes come from.
- One row per claim, not per source. If two sources support one claim, add a
  second row with the same claim text and the other source (this is also how
  `ai-verified` corroboration is evidenced).
- The verifier fails the page if a `sourced` row has no quote, if a cited Source
  has no row, or if an `unknown` claim's text appears on-page.
