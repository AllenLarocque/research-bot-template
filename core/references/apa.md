# APA citation formats (entity Source pages)

Put the finished string in the Source page's `citation` field. That field is the
single source of truth for the citation text — inline citation markers link back
to the Source page rather than repeating it.

- **Book:** Author, A. A. (Year). *Title in italics*. Publisher. ISBN.
  e.g., Drushka, K. (1995). *HR: A Biography of H.R. MacMillan*. Harbour Publishing.
- **Encyclopedia entry:** Author/Editor. (Year). Entry title. In *Encyclopedia name*. Publisher.
  e.g., Francis, D. (Ed.). (2000). Bloedel, Stewart & Welch. In *Encyclopedia of British Columbia*. Harbour Publishing.
- **News article:** Author, A. (Year, Month Day). Headline. *Publication*. URL
  e.g., Rothenburger, M. (2015, December 5). Domtar celebrates pulp mill's 50 years in Kamloops. *Kamloops This Week*. https://…
- **Web page / corporate site:** Organization. (Year). *Page title*. Site. URL
  e.g., West Fraser Timber Co. Ltd. (n.d.). *Our history*. West Fraser. https://…
- **Regulatory filing:** Company. (Year). *Form type: description* (Identifier). Regulator. URL
  e.g., Weyerhaeuser Company. (2000). *Form 8-K/A: Acquisition of MacMillan Bloedel Limited* (CIK 0000106535). U.S. Securities and Exchange Commission. https://…
- **Archival fonds:** *Fonds/record title* (dates). Repository. URL
  e.g., *British Columbia Forest Products Limited fonds* (1946–1987). Royal BC Museum, BC Archives. https://…

Notes:
- Prefer a retrieval date only for pages likely to change (wikis, live corporate pages).
- Give an ISBN for books.
- The Source page stores `url` and `archive_url` separately, so the APA string
  need not repeat them; including the URL in the citation is fine and matches APA.
- Use `n.d.` when a web page carries no publication date — never invent one.
- Wikipedia is tier T3: cite it in APA like any web page, but it may only
  corroborate, never solely carry an `ai-verified` claim (see `source-vetting`).

---

## Conversion completed (2026-07-28)

All **116 Source pages are now APA-formatted**. The corpus previously used a house style
(`"Title". ''Publication'', date. Accessed …`); it was converted mechanically by
`scratchpad/apaconv.py`, which pattern-matches the nine shapes that actually occurred and
refuses anything it cannot parse confidently. Sixty converted automatically; four were done by
hand (a multi-author CBC piece, an Encyclopedia.com company history, a UNBC subject guide, and
a Weyerhaeuser press release).

### Two formatting rules learned the hard way
1. **Italics must be wikitext `''…''`, never markdown `*…*`.** Forty-three Source pages created
   during this project used asterisks, which the wiki renders literally — the citations
   displayed `*Title*` instead of italics. All fixed.
2. **Titles that already end in a period** (e.g. `Kruger Inc.`) produce `Kruger Inc.. (2026)`
   unless de-duplicated. The converter collapses repeated periods.

### Independence warning recorded on the pages themselves
Two Source pages covered the same document (`West Fraser — About Us` contains
`West Fraser — Our History`). Both now carry an explicit note that they are NOT independent and
must never be counted as two corroborating sources. Check for this before adding a Source page
whose URL is a superset of an existing one.

## Acceptance check — existing Source pages vs. these formats (2026-07-27)

**Superseded by the 2026-07-28 conversion above — all four have since been reformatted.**
Retained as the original worked examples of what the house style looked like and how each
maps to APA.

Checked four live Source pages. All four predated this reference and used a
short house style rather than APA.

| Source page | Current `citation` (verbatim, fetched 2026-07-27) | Verdict |
|---|---|---|
| `HR A Biography of H.R. MacMillan` | `Drushka, Ken (1995). ''HR: A Biography of H.R. MacMillan''. Madeira Park, BC: Harbour Publishing. ISBN 1-55017-129-0.` | **Close, not APA.** Given name should be an initial; APA drops the place of publication. APA: `Drushka, K. (1995). ''HR: A Biography of H.R. MacMillan''. Harbour Publishing. ISBN 1-55017-129-0.` |
| `Wikipedia — Julius Bloedel` | `"Julius Bloedel". ''Wikipedia''. Accessed 18 July 2026.` | **Not APA.** APA: `Julius Bloedel. (2026). In ''Wikipedia''. Retrieved July 18, 2026, from https://en.wikipedia.org/wiki/Julius_Bloedel` |
| `SEC Form 8-K-A — Weyerhaeuser acquisition of MacMillan Bloedel` | `Weyerhaeuser Company (2000). Form 8-K/A, "Completion of acquisition of MacMillan Bloedel Limited" (event 1 November 1999). U.S. Securities and Exchange Commission, EDGAR (CIK 0000106535).` | **Close, not APA.** Needs a period after the author, the year in parentheses as its own sentence, and the form title in italics. APA: `Weyerhaeuser Company. (2000). ''Form 8-K/A: Completion of acquisition of MacMillan Bloedel Limited'' (CIK 0000106535). U.S. Securities and Exchange Commission.` |
| `Kamloops This Week — Domtar Pulp Mill 50 Years 2015` | `"Domtar celebrates pulp mill's 50 years in Kamloops". ''Kamloops This Week'', 5 December 2015.` | **Not APA.** No author credited on the piece, so the headline moves to the author slot. APA: `Domtar celebrates pulp mill's 50 years in Kamloops. (2015, December 5). ''Kamloops This Week''. https://…` |

Conclusion: the existing corpus is internally consistent but not APA. Converting
all 73 Source pages is a separate maintenance pass, not part of the skill build;
new and touched Source pages must use APA from now on.
