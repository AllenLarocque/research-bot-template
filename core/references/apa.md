# APA citation formats (entity Source pages)

Put the finished string in the Source page's `citation` field. That field is the
single source of truth for the citation text — inline citation markers link back
to the Source page rather than repeating it.

- **Book:** Author, A. A. (Year). *Title in italics*. Publisher. ISBN.
  e.g., Chandler, A. D. (1977). *The Visible Hand: The Managerial Revolution in American Business*. Harvard University Press.
- **Encyclopedia entry:** Author/Editor. (Year). Entry title. In *Encyclopedia name*. Publisher.
  e.g., Francis, D. (Ed.). (2000). Example Manufacturing Company. In *Encyclopedia of American Business*. Britannica Publishing.
- **News article:** Author, A. (Year, Month Day). Headline. *Publication*. URL
  e.g., Rothenburger, M. (2015, December 5). Domtar celebrates pulp mill's 50 years in Kamloops. *Kamloops This Week*. https://…
- **Web page / corporate site:** Organization. (Year). *Page title*. Site. URL
  e.g., West Fraser Timber Co. Ltd. (n.d.). *Our history*. West Fraser. https://…
- **Regulatory filing:** Company. (Year). *Form type: description* (Identifier). Regulator. URL
  e.g., Acme Corporation. (2000). *Form 8-K/A: Acquisition of Example Industries Limited* (CIK 0000000000). U.S. Securities and Exchange Commission. https://…
- **Archival fonds:** *Fonds/record title* (dates). Repository. URL
  e.g., *Example Manufacturing Company fonds* (1946–1987). Provincial Archives. https://…

Notes:
- Prefer a retrieval date only for pages likely to change (wikis, live corporate pages).
- Give an ISBN for books.
- The Source page stores `url` and `archive_url` separately, so the APA string
  need not repeat them; including the URL in the citation is fine and matches APA.
- Use `n.d.` when a web page carries no publication date — never invent one.
- Wikipedia is tier T3: cite it in APA like any web page, but it may only
  corroborate, never solely carry an `ai-verified` claim (see `source-vetting`).
- Titles are italicized per whatever the target output format uses for
  emphasis (wiki markup, Markdown, etc.) — this reference does not prescribe
  a specific markup syntax, only the APA shape.
- **Titles that already end in a period** (e.g. `Kruger Inc.`) can produce a
  double period (`Kruger Inc.. (2026)`) if the year parenthetical is appended
  naively — de-duplicate the repeated period.
- Watch for two Source pages covering the same underlying document (e.g. an
  "About Us" page that reproduces an "Our History" page verbatim): note the
  overlap on both pages and never count them as two independent corroborating
  sources.

The history of converting this project's corpus to APA, and the
format-specific rendering rule that conversion surfaced, are recorded in
`adapters/mediawiki/attribution/SKILL.md` (that history is tied to how one
specific wiki renders emphasis, not to the citation shapes above).
