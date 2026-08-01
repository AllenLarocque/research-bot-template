---
name: source-vetting
description: Use when assessing, choosing, or citing a source for an entity page, and whenever deciding between verification=ai-verified and unverified on a relationship. Establishes credibility tiers and the independence test.
---

# Source vetting

Decide two things about every source, before it is cited: **how credible is it**
(tier) and **is it independent** of the other sources supporting the same claim.

## Credibility tiers

- **T1 — primary / archival.** Government records, SEC and other regulatory
  filings, archival fonds (provincial or state archives, regional archive
  aggregators, university open collections), period
  newspapers, corporate primary documents (annual reports, prospectuses).
- **T2 — reputable secondary.** National and regional encyclopedias, scholarly
  books and articles by recognised historians of the field, established news
  outlets writing their own reporting.
- **T3 — tertiary / aggregator.** Wikipedia, company "our history" pages,
  industry directories. **May corroborate; may never solely carry an
  `ai-verified` claim.**
- **T4 — unreliable.** Grokipedia, open wikis, forums, content farms, LLM
  output. **Leads only — never cited.** Use them to find a real source, then
  cite that.

## The independence test

Two sources are independent only if **neither derives from the other and they
share no common origin.**

Not independent:
- Two outlets running the same wire story → counts as **one**.
- Wikipedia plus a source that Wikipedia cites → counts as **one**.
- A company's own page plus a news piece that quotes that company → weak;
  count as **one** unless the outlet did its own reporting.
- Two encyclopedia entries by the same author or publisher → **one**.

Independent:
- An SEC filing and a newspaper's own reporting on the same transaction.
- An archival fonds description and a scholarly book working from other records.

## The rule

`verification=ai-verified` requires **2+ independent T1/T2 sources.**

Anything less is `verification=unverified`, with a `note=` saying why (single
source; sources not independent; source is T3). Being honest here is the point
of the field — an `unverified` row is useful, a wrongly `ai-verified` row is
damage.

## Output

For each source, record in the ledger: **tier + a one-line justification.**
Flag borderline independence explicitly rather than resolving it silently.

## Worked test cases

**(a) CNN and Reuters both reporting a company's press release.**
Both trace to one origin — the press release. → **Not independent; counts as 1.**
A claim resting only on these is `unverified`. (If Reuters adds its own
reporting beyond the release, the added material may count separately.)

**(b) A national encyclopedia entry and a scholarly monograph, written independently.**
Two T2 sources, neither derived from the other. → **Independent; 2 of 2.**
Eligible for `ai-verified`.

**(c) Wikipedia article and the regional encyclopedia entry it cites as a reference.**
Derived. → **Not independent; counts as 1** — and the Wikipedia one is T3
anyway, so cite the regional encyclopedia directly instead.
