---
name: lr-4-intake
description: Stage 4 of the related-work pipeline. Defines the synthesis set (every paper read in full at priority 1–2), matches each to its library/refs.bib entry and PDF, files PDFs as library/pdfs/<citekey>.pdf, records citekeys, closes out every other candidate, and reports anything missing or mismatched.
disable-model-invocation: true
---

# Stage 4: Intake

**Purpose:** make sure every paper in the synthesis set has exactly one BibTeX entry and one PDF, named by citekey, before the synthesis reads them. The **synthesis set** is every paper read in full at priority 1–2: `python3 scripts/candidates.py list --status expanded --basis full-text --priority-max 2 --json`. Nothing is cut here; the synthesis (stage 5) decides what the section cites. After this stage, a record has a `citekey` exactly when it is in the synthesis set.

**Reads:** `research/candidates.jsonl`; `library/refs.bib` (and the PDFs in Zotero's storage that its `file` fields point to); `expand/*.pdf`; `library/inbox/*.pdf`.
**Writes:** `library/pdfs/<citekey>.pdf`, `library/intake-report.md`, `research/candidates.jsonl` (`citekey`, `pdf`, `status`, `decision_reason`), `STATUS.md`.
**Gate:** if the report lists problems, the human fixes them and reruns this stage. If it is clean, continue to `/lr-5-synthesize`.

## Steps

1. Read `STATUS.md` and follow the stage-start rule in `CLAUDE.md`: the gate is that stage 3 is `done` and `library/refs.bib` exists. If `refs.bib` does not exist, stop and ask the human to export the Zotero collection there (see step 1 of *What to do* in `manual/fetch-for-expand.md`).

2. **Close out the other candidates.** Every record not in the synthesis set and not already `reject` becomes `reject`, with `python3 scripts/candidates.py set <id> status=reject decision_reason="<reason>"`:
   - read in full but priority 3–4: "read in full, priority <n>";
   - priority 1–2 but never read in full (its `decision_reason` says the PDF is not available): "priority <n>, PDF not available". List these under **Not read in full** in the report: the synthesis cannot use them, and the human may want to find their PDFs and rerun `/lr-3-expand`;
   - everything else: "not read in full (priority <n>)".

3. **Match records to BibTeX entries.** `python3 scripts/bib.py list` prints every entry's key, title, DOI and arXiv ID. For each paper in the synthesis set (the list command above includes `ids` and `pdf`), find its entry with `python3 scripts/bib.py match --doi <doi>`, `--arxiv <id>` or `--title "<title>"`, in that order. Record it: `candidates.py set <id> citekey=<key>`.
   - No entry: list under **Missing from refs.bib**.
   - Entry is an arXiv preprint but the record has a DOI for a published version: list under **Preprint entries** (the human may want to replace them in Zotero).
   - BibTeX entries that match no paper in the set: give only their number under **Extra entries**. They are expected when the collection holds every paper saved; the writer cites only papers the synthesis chooses.

4. **File PDFs.**
   - Papers whose `pdf` is in `expand/`: **copy** (do not move) to `library/pdfs/<citekey>.pdf`.
   - Papers with no `pdf`: copy from Zotero's storage with `python3 scripts/bib.py pdf <citekey> --copy-to library/pdfs/<citekey>.pdf` (it never overwrites a different file).
   - PDFs in `library/inbox/` (a fallback for papers whose PDF is not in Zotero): read **only the first page** of each to get its title; match it to a paper in the set with a citekey (normalized title; check authors if the title is generic). **Move** it to `library/pdfs/<citekey>.pdf`. If you cannot match it confidently, leave it in the inbox and list it under **Unmatched PDFs**.
   - Then `candidates.py set <id> pdf=library/pdfs/<citekey>.pdf` for every filed paper.
   - Never overwrite an existing `library/pdfs/<citekey>.pdf` with a different file; list conflicts instead.

5. **Check completeness.** Every paper in the set needs a citekey and a PDF in `library/pdfs/`. List any that do not under **Missing PDFs**.

6. **Write `library/intake-report.md`** with a summary line ("<n> of <m> papers in the synthesis set complete") and the sections above (omit empty ones). Run `candidates.py validate`.

7. **Update `STATUS.md`:** stage 4 `done` if every paper in the set is complete, otherwise `waiting on human`; date; next action accordingly ("Run `/lr-5-synthesize`" or "Human fixes the items in `library/intake-report.md` and reruns `/lr-4-intake`"). *Not read in full* alone does not hold the stage open.

8. **Report** the summary line, the size of the synthesis set, and the problem sections.
