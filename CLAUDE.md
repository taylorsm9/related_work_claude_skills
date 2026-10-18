# Related-work pipeline: agent instructions

This repository produces the related-work section of an implementation paper. It runs as a sequence of stages. Each stage has a skill in `.claude/skills/lr-<n>-<name>/SKILL.md` that says what it reads, what it writes and when it is done. Some stages are done by the human; the pipeline stops and waits for them.

**Before doing anything, read `STATUS.md`.** It says which stage is current and whether a human gate is open. Do not start a stage whose inputs are not ready, and do not skip a gate.

## Stages

| # | Stage | Skill | Done by | Gate after |
|---|---|---|---|---|
| 0 | Contributions | `/lr-0-contributions` | Agent drafts, human approves | Human sets `status: approved` in `project/contributions.md` |
| 1 | Search | `/lr-1-search` | Agent | Human reviews `manual/fetch-for-expand.md` |
| 2 | Fetch for expand | — | **Human** | Human puts PDFs in `expand/` and says so |
| 3 | Expand | `/lr-3-expand` | Agent + `paper-reader` subagents | Human may add more PDFs to `expand/` and rerun |
| 4 | Screen | `/lr-4-screen` | Agent proposes, human decides | Human fills the decision column in `research/shortlist.md` |
| 5 | Fetch the rest | `/lr-5-fetch` | Agent writes list, **human** fetches | Human: PDFs in `library/inbox/`, Zotero export at `library/refs.bib` |
| 6 | Intake | `/lr-6-intake` | Agent | Human resolves anything flagged in `library/intake-report.md` |
| 7 | Notes | `/lr-7-notes` | Agent + `note-writer` subagents | Human reviews `notes/overview.md` |
| 8 | Draft | `/lr-8-draft` | Agent, fresh session | — |
| 9 | Humanize | `/lr-9-humanize` | humanizer skill + cite-key check | — |
| 10 | Check | `/lr-10-check` | Agent + `citation-checker` subagents | Human final review |

## Global rules

**Citations and identifiers**
- Never write a citation, title, author list, DOI or arXiv ID from memory. Every identifier must come from a tool result (`scripts/lit.py`, a PDF, or `library/refs.bib`).
- In writing stages, cite only keys that exist in `library/refs.bib`.
- Never claim a paper says something unless a quote with a page number supports it.

**Papers and sources**
- Do not download papers. The human fetches every PDF. Use `scripts/lit.py` for metadata and abstracts only.
- Do not automate Google Scholar, and never use Sci-Hub or similar sources.
- Use `scripts/lit.py` for all arXiv, Semantic Scholar and DBLP calls, and log every search in `research/search-log.md` using the columns in `templates/search-log.md` (date, stage, source, query or seed, filters, hits, new candidates).

**Subagents**
- Use the project subagents by name: `candidate-assessor`, `paper-reader`, `note-writer`, `citation-checker`.
- **Do not pass a `model` or `effort` parameter when spawning them.** Their definition files pin the model and effort on purpose; a launch parameter would override that. Never substitute `general-purpose`, Explore or a lighter model for these jobs.
- One PDF per `paper-reader`, `note-writer` or `citation-checker`. Run several in parallel (up to about 5 at once).
- Subagents write their own output files and return a one-line status. Do not ask them to paste results back into the conversation.

**Files and state**
- Only the main session writes `research/candidates.jsonl` and `STATUS.md`. Subagents never edit them; the main session merges their output files.
- Do not read whole PDFs in the main session. Reading is the subagents' job; the main session may read a PDF's first page only to identify it.
- File names use a paper's slug before it has a citekey, and its citekey after intake (stage 6). See `templates/schemas.md` for IDs and slugs.
- Data formats for every machine-read file are in `templates/schemas.md`. Validate with `python3 scripts/candidates.py validate` after every write to `candidates.jsonl`.
- Two records for one paper (often a preprint and its published version): `candidates.py add` folds them automatically when an identifier links them; otherwise use `python3 scripts/candidates.py merge <id to keep> <id to drop>`. Never edit `candidates.jsonl` by hand.
- To see a record's `ids`, `pdf` or other fields, use `python3 scripts/candidates.py list … --json`, not the raw file.

**STATUS.md**
- **At the start of a stage:** check that the gate before it is met, as the stage's step 1 describes. If it is, mark every earlier stage `done` (including the human stages in between), set this stage `in progress`, and set **Current stage** to this stage. If it is not, stop and say what is missing.
- **At the end of a stage:** mark it `done` or `waiting on human`, record the date, set **Current stage** to the next stage, and write the next action in one line.

**Human gates**
- When a stage ends at a gate, stop. Tell the human exactly what to do, which file to edit, and which skill to run next.

## Map

```
project/        the human's paper draft + contributions.md (C1, C2, …)
research/       candidates.jsonl (one record per paper), search-log.md, shortlist.md,
                assessments/ (candidate-assessor output), expand/ (paper-reader output)
expand/         PDFs for the expand stage (fetched by the human; extras welcome)
manual/         task files written for the human (fetch lists)
library/        refs.bib (Zotero export), inbox/ (fetched PDFs), pdfs/<citekey>.pdf, intake-report.md
notes/          <citekey>.md per kept paper, overview.md
writing/        related_work.tex and saved versions
checks/         <citekey>.json per cited paper, report.md
templates/      file templates and schemas.md
scripts/        lit.py (APIs), candidates.py, bib.py, cites.py
```

## Helper scripts

All are Python 3 standard library only. Run them from the repo root.

- `python3 scripts/lit.py <command> …` — arXiv, Semantic Scholar and DBLP lookups. Prints JSON. `python3 scripts/lit.py -h` lists commands. Uses `S2_API_KEY` from the environment if set.
- `python3 scripts/candidates.py validate | render | stats | find …` — checks and renders `research/candidates.jsonl`.
- `python3 scripts/bib.py list | match …` — reads `library/refs.bib`.
- `python3 scripts/cites.py keys | compare | check-bib | sentences …` — citation keys in LaTeX files.
