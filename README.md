# Related-work pipeline template

A Claude Code project template for writing the related-work section of an implementation paper. It searches arXiv, Semantic Scholar and DBLP, reads the papers you fetch, follows their references and citing papers, and judges every paper against your stated contributions. It then writes notes with quoted evidence, drafts the section citing only your Zotero BibTeX keys, edits it with humanizer, and checks every citation against its paper.

It is built for a small, curated set (under about 20 papers). You fetch every PDF yourself; the agents never download papers.

## Requirements

- Claude Code 2.1.292 or newer. The subagent definitions pin `model` and `effort`, and per-launch effort handling needs this version.
- Python 3.9+ (standard library only).
- Zotero with Better BibTeX, for the bibliography.
- humanizer (https://github.com/blader/humanizer), for stage 9:
  ```
  /plugin marketplace add blader/humanizer
  /plugin install humanizer@humanizer
  ```
- Optional: a Semantic Scholar API key (free, request at semanticscholar.org/product/api) in `S2_API_KEY`. Without it requests share a throttled pool and may fail with HTTP 429.

### Environment variables to leave unset

These override the pinned subagent settings:

- `CLAUDE_CODE_EFFORT_LEVEL` overrides the effort set in every subagent definition.
- `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` makes Claude Code ignore the `model` in subagent definitions.

## Subagent models

The reading-heavy subagents run on Opus with high effort, because reading quality decides what the pipeline finds:

| Subagent | Job | Model | Effort |
|---|---|---|---|
| `paper-reader` | Expand: reads one PDF in full, judges it, pulls relevant references | `claude-opus-5-5` | `xhigh` |
| `note-writer` | Notes: one evidence note per kept paper | `claude-opus-5-5` | `xhigh` |
| `citation-checker` | Check: every sentence citing one paper, against the PDF | `claude-opus-5-5` | `xhigh` |
| `candidate-assessor` | Search/expand: judges batches of candidates from abstracts | `claude-opus-5-5` | `high` |

The model is pinned by full ID. To follow newer Opus releases automatically, change `model: claude-opus-5-5` to `model: opus` in `.claude/agents/*.md`.

## Starting a project

1. Create a new repository from this template (GitHub: **Use this template**), and clone it.
2. Put your paper draft in `project/`.
3. Open Claude Code in the repository and run the stages in order. Each one stops when it needs you.

| # | Run | You then |
|---|---|---|
| 0 | `/lr-0-contributions` | Edit `project/contributions.md`; set `status: approved` |
| 1 | `/lr-1-search` | Read `manual/fetch-for-expand.md` |
| 2 | — | Download those PDFs into `expand/` (any filenames). Add any other PDFs you found yourself |
| 3 | `/lr-3-expand` | Optionally add more PDFs to `expand/` and run it again |
| 4 | `/lr-4-screen` | Fill in the decision column in `research/shortlist.md` |
| 5 | `/lr-5-fetch` | Put the kept papers in a Zotero collection; auto-export it with Better BibTeX to `library/refs.bib`; drop missing PDFs in `library/inbox/` |
| 6 | `/lr-6-intake` | Fix anything in `library/intake-report.md` |
| 7 | `/lr-7-notes` | Review `notes/overview.md` |
| 8 | `/clear`, then `/lr-8-draft` | — |
| 9 | `/lr-9-humanize` | — |
| 10 | `/lr-10-check` | Read `checks/report.md`; final edits are yours |

`STATUS.md` always shows where the pipeline is and what's next. You can add a PDF to `expand/` at any point up to stage 4: the expand stage identifies it, judges it against your claims and records it as found manually.

## What's in the repository

- `CLAUDE.md`: rules every agent follows, the stage table and the file map.
- `.claude/skills/lr-*`: one instruction file per stage.
- `.claude/agents/`: the four subagent definitions.
- `templates/`: file templates and `schemas.md`, the data formats.
- `scripts/`: `lit.py` (arXiv, Semantic Scholar, DBLP lookups), `candidates.py`, `bib.py`, `cites.py`.

PDFs are ignored by git (`.gitignore`), since most are copyrighted. Keep that if the repository is public.

## Notes

- **Google Scholar** is not automated: it has no API and blocks automated access. If you find a paper there, drop its PDF in `expand/`.
- The helper scripts were written against the documented arXiv, Semantic Scholar and DBLP APIs but not yet run against the live services. Try `python3 scripts/lit.py s2-search --query "test" --limit 1` once before a real run.
