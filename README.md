# Related-work skills for Claude Code

These skills are research tools for writing a paper's related-work section. The quantity of papers such a section draws on would overload a language model's context if loaded all at once. Instead, each paper is read by its own subagent and condensed two ways: against your paper's contributions, and against a taxonomy of the field learned from the related-work sections of those same papers. The taxonomy-based summaries become a concept matrix of papers against concepts, small enough to show the whole field in one context. The matrix is an established method for literature reviews (Webster and Watson's guide; Judith Garrard's *Health Sciences Literature Review Made Easy: The Matrix Method*). The synthesis stage uses it to group the papers, place yours among them, and choose what to cite. Optionally, an experimental set of drafting skills then writes a first draft of the section.

Use the repository as a project template: one skill per stage, with nine subagents and helper scripts, built for implementation papers. It searches arXiv, Semantic Scholar and DBLP, reads the papers you fetch, follows their references and citing papers, and judges every paper against your stated contributions. It then builds the taxonomy and the concept matrix, chooses which papers to cite, writes notes with quoted evidence for them, drafts the section citing only your Zotero BibTeX keys, edits it with humanizer, and checks every citation against its paper.

It reads every paper that looks relevant in full, typically several dozen, and then chooses on its own which of them the section cites. You save every paper into a Zotero collection yourself; the agents never download papers, and take the PDFs from Zotero.

It looks for work close to your stated contributions. It is not built to find anchor citations, such as the paper that introduced a technique or a standard benchmark. Those usually belong in the introduction rather than the related-work section; add them yourself.

## Requirements

- Claude Code 2.1.292 or newer. The subagent definitions pin `model` and `effort`, and per-launch effort handling needs this version.
- Python 3.9+ (standard library only).
- Zotero with the browser connector and Better BibTeX. Create one collection for the paper and set up a Better BibTeX automatic export of it (format *Better BibTeX*, *Keep updated* ticked) to `library/refs.bib`. The pipeline reads both the metadata and the PDF paths (the `file` field) from that file.
- humanizer (https://github.com/blader/humanizer), for stage 8:
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
| `note-writer` | Notes: one evidence note per cited paper | `claude-opus-5-5` | `xhigh` |
| `citation-checker` | Check: every sentence citing one paper, against the PDF | `claude-opus-5-5` | `xhigh` |
| `paper-summarizer` | Synthesize: one claim-free summary per paper, guided by the field taxonomy | `claude-opus-5-5` | `xhigh` |
| `taxonomy-builder` | Synthesize: the field's categories, from every paper's related-work section | `claude-opus-5-5` | `xhigh` |
| `literature-mapper` | Synthesize: the comparison table; also checks one property in one PDF | `claude-opus-5-5` | `xhigh` |
| `synthesis-reviewer` | Synthesize: fresh-eyes review of the synthesis, in place of a human gate | `claude-opus-5-5` | `xhigh` |
| `candidate-assessor` | Search/expand: judges batches of candidates from abstracts | `claude-opus-5-5` | `high` |
| `related-work-extractor` | Synthesize: one paper's related-work section, verbatim, citations resolved | `claude-opus-5-5` | `high` |

The model is pinned by full ID. To follow newer Opus releases automatically, change `model: claude-opus-5-5` to `model: opus` in `.claude/agents/*.md`.

## Starting a project

1. Create a new repository from this template (GitHub: **Use this template**), and clone it.
2. Put your paper draft in `project/`.
3. Open Claude Code in the repository and run the stages in order. Each one stops when it needs you. You are needed through stage 3 (approving the claims, saving papers into Zotero each round); from stage 4 on it runs on its own, stopping only if intake finds a problem, until your final review.

| # | Run | You then |
|---|---|---|
| 0 | `/lr-0-contributions` | Edit `project/contributions.md`; set `status: approved` |
| 1 | `/lr-1-search` | Read `manual/fetch-for-expand.md` |
| 2 | — | Save those papers into the Zotero collection with their PDFs. Add any other papers you found yourself |
| 3 | `/lr-3-expand` | Runs in rounds. After each round, save the next round's papers (listed in `manual/fetch-for-expand.md`) into Zotero and run it again, until every probably-relevant paper has been read |
| 4 | `/lr-4-intake` | Fix anything in `library/intake-report.md` (usually nothing) |
| 5 | `/lr-5-synthesize` | — |
| 6 | `/lr-6-notes` | — |
| 7 | `/clear`, then `/lr-7-draft` | — |
| 8 | `/lr-8-humanize` | — |
| 9 | `/lr-9-check` | Read `checks/report.md`; final edits are yours |

Stages 7–9 are the experimental drafting skills. You can stop after stage 6 and write the section yourself from `notes/synthesis.md` (the concept matrix's groups, the positioning against your paper, and the papers to cite) and the evidence notes in `notes/`.

`STATUS.md` always shows where the pipeline is and what's next. You can save extra papers into the Zotero collection, or drop PDFs into `expand/`, at any point before the last expand round: the expand stage identifies them, judges them against your claims and records them as found manually.

The fetch lists link arXiv abstract pages rather than PDFs, so the Zotero connector picks up full metadata. Papers that also have a published version (proceedings or journal) are listed separately, with a link to that version where Semantic Scholar has one.

## What's in the repository

- `CLAUDE.md`: rules every agent follows, the stage table and the file map.
- `.claude/skills/lr-*`: one instruction file per stage.
- `.claude/agents/`: the nine subagent definitions.
- `templates/`: file templates and `schemas.md`, the data formats.
- `scripts/`: `lit.py` (arXiv, Semantic Scholar, DBLP lookups), `candidates.py`, `bib.py`, `cites.py`, `digest.py`.

PDFs are ignored by git (`.gitignore`), since most are copyrighted. Keep that if the repository is public.

## The synthesis stage

The expand stage judges each paper against your claims, one at a time. A draft built only from those judgments tends to list papers, organize itself around your claims, and miss papers that resemble yours in ways the claims never asked about. Stage 5 builds the structure from the literature first, over every paper read in full at priority 1–2. It extracts each paper's related-work section, builds a taxonomy of how the field divides itself, summarizes each paper against that taxonomy without seeing your claims, and builds a comparison table. Only then does it add your paper, look for close work the expand-stage judgments missed, and write `notes/synthesis.md`: groups, positioning corrections, things not to say, a suggested paragraph plan, and the papers to cite. A fresh-context reviewer checks it in place of a human gate. Evidence notes are then written only for the cited papers, and each note checks what the plan says about its paper against the PDF.

Cost: each paper read in full is read twice more, lightly for its related-work section and in full for its summary, plus one run each of the taxonomy builder, mapper and reviewer (reviewer up to twice). The taxonomy builder and mapper read digests built by `scripts/digest.py`, so a set of about 70 papers fits. Expect roughly 100–200k subagent tokens and 5–12 minutes per summary; with about 70 papers the stage comes to several million tokens. It is by far the most expensive stage.

Background:
- Webster & Watson's guide to literature reviews argues for organizing by concept, using a concept matrix of papers × concepts.
- In Li & Ouyang (arXiv 2402.13426), experts disliked generated related work that strung per-paper summaries together and compared the cited works weakly. Human-written sections relied on sentences relating several papers.
- In CHIME (arXiv 2407.16148), LLMs built sensible category hierarchies but assigned studies to categories poorly. Using the field's own placements, and checking each placement, addresses this.

## Notes

- **Google Scholar** is not automated: it has no API and blocks automated access. If you find a paper there, save it into the Zotero collection.
- **DBLP** currently answers scripted requests with a bot-check page, so DBLP searches fail and are logged as failures. Links to published versions come from Semantic Scholar instead.
- The arXiv and Semantic Scholar lookups were used against the live services in the test run. Without an `S2_API_KEY`, Semantic Scholar sometimes answers HTTP 429; the failed searches are logged and can be rerun.
