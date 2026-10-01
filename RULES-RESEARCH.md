# Research rules

Rules for any research bot that writes sourced text from fetched documents.
One sentence each. The incident behind a rule is in this file's git history.

## Before you fetch

- Search what you already hold first — the captures, the ledgers, the design notes; the answer is often already in the corpus.
- When a site has a machine-readable index or API, use it before building URLs by hand.
- Send a User-Agent; a 403 to a bare request may only be asking who you are.
- When several searches on one subject have failed, change the kind of record you search, not the search terms.

## When you fetch

- A 200 is not the document: read the title and the size of what came back; error pages, challenges and subscription previews all answer 200.
- A failed fetch is recorded as a failure, never saved as a capture.
- Every URL you cite has a capture and a sidecar naming that URL; no capture, no citation.
- Re-fetch before you cite an older capture; if the live page has gone, say so on the Source page, and if the Archive is down, say that rather than that no copy exists.
- Take a Wayback URL from the availability API's exact timestamp; a dated path can return the site's home page.
- Copy a URL into a ledger row from the sidecar, never from memory or from another row's pattern.

## When you quote

- A quotation is copied from the capture, never reconstructed: extract the span by position, because retyping recapitalises, straightens apostrophes, drops markers, and passes every check.
- Quote the characters a reader sees: unescape entities, and quote from the stripped rendering of an HTML capture.
- An ellipsis marks an omission within one passage of one source; never join two sources with one.
- Read any name or number you quote from OCR against the page image, and the column headings before a table row; if the image does not settle it, say the source contains it and stop.
- Quote a span long enough for the checker to find once; a single short token fails `snapcheck`, so take a longer span or leave the detail out.
- Collapse whitespace in a quotation before it goes into a table cell; a newline silently breaks every row below it.
- Quote JSON as its values joined by ellipses, never as key/value pairs; the checker reads a cell between quote marks.
- Repair a wrong quotation against the capture its own citation names, one row at a time, never by string replace.
- Never write an editorial mark inside quotation marks; retract by wrapping the text in ‹ › with the reason before it, and never erase.
- Never quote a person's contact details from a captured letter onto a page.

## When you weigh sources

- Two sources that agree word for word are one source; read a full sentence of each before counting two.
- A syndicated story is one witness; cite one copy and waive the rest.
- Absence of a quote from your captures is not evidence the source lacks it; search every capture and re-fetch at the recorded address before calling a quote invented.
- Prefer primary and archival records over aggregators.

## When you record

- Every ledger row carries its quote, its literal URL and the capture filename, one source per row.
- Grep the ledgers for a capture's filename before deleting it.
- Edit a ledger with `ledgertrim`, never with a regex over the file.
- Search captures with a whitespace-tolerant pattern; OCR and djvu text break lines inside sentences.
- If you add to a waiver queue, write the verdict in the same pass.
- Check what you just wrote, not what has stood for weeks; defects concentrate in fresh work.

## When you write a tool

- A probe answers one question and lives in `/dossiers/_tools/`; name one worth keeping in your handover.
- A tool that gates publication or is cited in a handover is infrastructure: `__main__` guard, dry run by default with `--write`, a `--selftest` that plants the defect, no absolute path outside `/dossiers`.
- A checker that cannot fail is worse than none: zero rows read is a broken query, so raise.
- A gate not in the battery manifest is not a gate; add a new checker to it in the same tick.

## Your notes

| file | reader | holds |
|---|---|---|
| `/dossiers/_PICKUP.md` | the next tick | the present: state, queue, decisions for a human, a pointer to leads |
| `/dossiers/_design/HANDOVER-<brief>.md` | whoever picks up the subject | what the brief found and decided, written once when it finishes |
| `/dossiers/_design/LEADS.md` | a tick with an empty queue | sourced leads not yet written, appended |
| `/dossiers/_runs.md` | an auditor | one entry per tick, appended forever |

- The pickup note keeps five headings in order — `# Pickup note — <date>`, `## State`, `## Queue`, `## Needs a human`, `## Leads` — under 150 lines with at most fifteen numbered queue items; `notecheck` holds it there.
- A queue item is at most two sentences — what, where its list is, how to re-derive it. When it closes, delete it; a lead goes to the leads file; per-tick detail goes to `_runs.md`; a lesson goes to a rulebook by way of your handover; nothing else goes in the note.
- When a fact in the note stops being true, replace the sentence; never append a section that takes an earlier one back.
- A handover is written once; correct it in place if you must, never append a dated section.
