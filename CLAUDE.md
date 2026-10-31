# Related-work pipeline: agent instructions

This repository produces the related-work section of an implementation paper. It runs as a sequence of stages. Each stage has a skill in `.claude/skills/lr-<n>-<name>/SKILL.md` that says what it reads, what it writes and when it is done. Some stages are done by the human; the pipeline stops and waits for them.

**Before doing anything, read `STATUS.md`.** It says which stage is current and whether a human gate is open. Do not start a stage whose inputs are not ready, and do not skip a gate.

## Stages

| # | Stage | Skill | Done by | Gate after |
|---|---|---|---|---|
| 0 | Contributions | `/lr-0-contributions` | Agent drafts, human approves | Human sets `status: approved` in `project/contributions.md` |
| 1 | Search | `/lr-1-search` | Agent | Human reviews `manual/fetch-for-expand.md` |
| 2 | Fetch for expand | — | **Human** | Human saves the listed papers, with PDFs, into the project's Zotero collection (auto-exported to `library/refs.bib`) |
| 3 | Expand (in rounds) | `/lr-3-expand` | Agent + `paper-reader` subagents | Until every priority 1–2 candidate is read: human saves each round's papers into Zotero and reruns |
| 4 | Intake | `/lr-4-intake` | Agent | Human resolves anything flagged in `library/intake-report.md` |
| 5 | Synthesize | `/lr-5-synthesize` | Agent + synthesis subagents; chooses the papers to cite; `synthesis-reviewer` replaces human review | — |
| 6 | Notes | `/lr-6-notes` | Agent + `note-writer` subagents, for the cited papers | — |
| 7 | Draft | `/lr-7-draft` | Agent, fresh session | — |
| 8 | Humanize | `/lr-8-humanize` | humanizer skill + cite-key check | — |
| 9 | Check | `/lr-9-check` | Agent + `citation-checker` subagents | Human final review |

## Global rules

**Citations and identifiers**
- Never write a citation, title, author list, DOI or arXiv ID from memory. Every identifier must come from a tool result (`scripts/lit.py`, a PDF, or `library/refs.bib`).
- In writing stages, cite only keys that exist in `library/refs.bib`.
- Never claim a paper says something unless a quote with a page number supports it.

**Papers and sources**
- Do not download papers. The human saves every paper, with its PDF, into the project's Zotero collection, which Better BibTeX auto-exports to `library/refs.bib`; scripts copy the PDFs from there (`candidates.py collect-pdfs`, `bib.py pdf`). Use `scripts/lit.py` for metadata and abstracts only.
- Fetch lists (`manual/*.md`) link arXiv **abstract pages** (`https://arxiv.org/abs/<id>`), never PDF links, so Zotero's connector picks up the metadata. Papers with a version outside arXiv go in a separate list with links from `lit.py published-links`. See `templates/fetch-list.md`.
- Do not automate Google Scholar, and never use Sci-Hub or similar sources.
- Use `scripts/lit.py` for all arXiv, Semantic Scholar and DBLP calls, and log every search in `research/search-log.md` using the columns in `templates/search-log.md` (date, stage, source, query or seed, filters, hits, new candidates).

**Subagents**
- Use the project subagents by name: `candidate-assessor`, `paper-reader`, `note-writer`, `citation-checker`, and for the synthesis stage `related-work-extractor`, `taxonomy-builder`, `paper-summarizer`, `literature-mapper`, `synthesis-reviewer`.
- **Do not pass a `model` or `effort` parameter when spawning them.** Their definition files pin the model and effort on purpose; a launch parameter would override that. Never substitute `general-purpose`, Explore or a lighter model for these jobs.
- One PDF per `paper-reader`, `note-writer`, `citation-checker`, `related-work-extractor`, `paper-summarizer` or `literature-mapper` in verify mode. Run several in parallel (up to about 5 at once).
- Subagents write their own output files and return a one-line status. Do not ask them to paste results back into the conversation.

**Files and state**
- Only the main session writes `research/candidates.jsonl` and `STATUS.md`. Subagents never edit them; the main session merges their output files.
- Do not read whole PDFs in the main session. Reading is the subagents' job; the main session may read a PDF's first page only to identify it.
- File names use a paper's slug before it has a citekey, and its citekey after intake (stage 4). See `templates/schemas.md` for IDs and slugs.
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
research/       candidates.jsonl (one record per paper), search-log.md,
                assessments/ (candidate-assessor output), expand/ (paper-reader output)
expand/         PDFs for the expand stage (copied from Zotero, or dropped in by the human)
manual/         task files written for the human (fetch lists)
library/        refs.bib (Better BibTeX export of the Zotero collection, with PDF paths),
                inbox/ (PDFs not in Zotero), pdfs/<citekey>.pdf, intake-report.md
notes/          synthesis stage: field/ (related-work extractions, papers.md, digest.md),
                field-taxonomy.md, summaries/ (claim-free summaries), summaries-digest.md,
                ours-summary.md, synthesis-map.md, synthesis-verify/,
                synthesis.md (synthesis, paragraph plan, papers to cite), synthesis-review.md;
                notes stage: <citekey>.md per cited paper
writing/        related_work.tex and saved versions
checks/         <citekey>.json per cited paper, report.md
templates/      file templates and schemas.md
scripts/        lit.py (APIs), candidates.py, bib.py, cites.py, digest.py
```

## Helper scripts

All are Python 3 standard library only. Run them from the repo root.

- `python3 scripts/lit.py <command> …` — arXiv, Semantic Scholar and DBLP lookups. Prints JSON. `python3 scripts/lit.py -h` lists commands. Uses `S2_API_KEY` from the environment if set.
- `python3 scripts/candidates.py validate | render | stats | find | collect-pdfs …` — checks and renders `research/candidates.jsonl`; `collect-pdfs` copies listed papers' PDFs from the Zotero export into `expand/`.
- `python3 scripts/bib.py list | match | show | pdf …` — reads `library/refs.bib`; `pdf` finds (and copies) an entry's PDF in Zotero's storage.
- `python3 scripts/cites.py keys | compare | check-bib | sentences …` — citation keys in LaTeX files.
- `python3 scripts/digest.py --title … --section … --out … FILE…` — concatenates named sections of Markdown files into one digest (synthesis stage).
