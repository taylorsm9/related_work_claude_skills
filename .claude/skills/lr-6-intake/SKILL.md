---
name: lr-6-intake
description: Stage 6 of the related-work pipeline. Matches every kept paper to its library/refs.bib entry and PDF, files PDFs as library/pdfs/<citekey>.pdf, records citekeys, and reports anything missing or mismatched.
disable-model-invocation: true
---

# Stage 6: Intake

**Purpose:** make sure every kept paper has exactly one BibTeX entry and one PDF, named by citekey, before any notes are written.

**Reads:** `research/candidates.jsonl` (status `keep`); `library/refs.bib`; `library/inbox/*.pdf`; `expand/*.pdf`.
**Writes:** `library/pdfs/<citekey>.pdf`, `library/intake-report.md`, `research/candidates.jsonl` (`citekey`, `pdf`), `STATUS.md`.
**Gate:** if the report lists problems, the human fixes them and reruns this stage. If it is clean, continue to `/lr-7-notes`.

## Steps

1. Read `STATUS.md` and follow the stage-start rule in `CLAUDE.md`: the gate is that `library/refs.bib` exists (the human finished stage 5). If it does not exist, stop and ask the human to export the Zotero collection there (see `manual/fetch-final.md`).

2. **Match records to BibTeX entries.** `python3 scripts/bib.py list` prints every entry's key, title, DOI and arXiv ID. For each kept candidate (`python3 scripts/candidates.py list --status keep --json`, which includes `ids` and `pdf`), find its entry with `python3 scripts/bib.py match --doi <doi>`, `--arxiv <id>` or `--title "<title>"`, in that order. Record it: `candidates.py set <id> citekey=<key>`.
   - No entry: list under **Missing from refs.bib**.
   - Entry is an arXiv preprint but the record has a DOI for a published version: list under **Preprint entries** (the human may want to replace them in Zotero).
   - BibTeX entries that match no kept paper: list under **Extra entries** (they may be fine, but the writer can only cite kept papers with notes).

3. **File PDFs.**
   - Kept papers whose `pdf` is in `expand/`: **copy** (do not move) to `library/pdfs/<citekey>.pdf`.
   - PDFs in `library/inbox/`: read **only the first page** of each to get its title; match it to a kept paper with a citekey (normalized title; check authors if the title is generic). **Move** it to `library/pdfs/<citekey>.pdf`. If you cannot match it confidently, leave it in the inbox and list it under **Unmatched PDFs**.
   - Then `candidates.py set <id> pdf=library/pdfs/<citekey>.pdf` for every filed paper.
   - Never overwrite an existing `library/pdfs/<citekey>.pdf` with a different file; list conflicts instead.

4. **Check completeness.** Every kept paper needs a citekey and a PDF in `library/pdfs/`. List any that do not under **Missing PDFs**.

5. **Write `library/intake-report.md`** with a summary line ("<n> of <m> kept papers complete") and the sections above (omit empty ones). Run `candidates.py validate`.

6. **Update `STATUS.md`:** stage 6 `done` if every kept paper is complete, otherwise `waiting on human`; date; next action accordingly ("Run `/lr-7-notes`" or "Human fixes the items in `library/intake-report.md` and reruns `/lr-6-intake`").

7. **Report** the summary line and the problem sections.
