---
name: lr-7-notes
description: Stage 7 of the related-work pipeline. Writes one evidence note per kept paper with note-writer subagents, then builds notes/overview.md (papers × claims, closest prior work, themes, bounded novelty statement).
disable-model-invocation: true
---

# Stage 7: Notes

**Purpose:** produce the material the section is drafted from: one note per kept paper, with quoted evidence, and an overview that compares the papers.

**Reads:** kept records in `research/candidates.jsonl`; `library/pdfs/<citekey>.pdf`; `research/expand/<slug>.json`; `project/contributions.md`; `templates/note.md`, `templates/overview.md`.
**Writes:** `notes/<citekey>.md` (via subagents), `notes/overview.md`, `STATUS.md`.
**Gate:** the human reviews `notes/overview.md` (especially the themes and the closest prior work per claim), then runs `/lr-8-draft` in a fresh session.

## Steps

1. Read `STATUS.md` and follow the stage-start rule in `CLAUDE.md`: the gate is that every kept paper has a citekey and a PDF in `library/pdfs/` (check with `candidates.py list --status keep`, last column, and the files). If not, stop and point to `library/intake-report.md`.

2. **Notes, one subagent per paper.** For each kept paper without a `notes/<citekey>.md`, spawn one `note-writer`, at most about 5 at a time. **Do not pass model or effort.** Give each: `citekey`, the paper's JSON line from `research/candidates.jsonl`, `pdf: library/pdfs/<citekey>.pdf`, `expand_file` (the record's `expand_file`, or `null`), and `output: notes/<citekey>.md`. Wait for all of them.

3. **Check the notes** without reading the PDFs: every note has every section of `templates/note.md`, a verdict for every claim, and at least one numbered evidence quote with a page. Re-spawn the `note-writer` for any note that does not.

4. **Write `notes/overview.md`** from `templates/overview.md`, using the notes and `python3 scripts/candidates.py stats` (for *N*, the number of candidates screened in total):
   - **Papers × claims** from the notes' verdicts.
   - **Closest prior work per claim:** the nearest paper(s) and the precise difference, taken from each note's *How our work differs*.
   - **Themes:** 2–4 groups that the section's paragraphs will follow. Group by what the papers do relative to the claims (for example, "systems that do X without Y"), not by publication year. Every kept paper belongs to at least one theme.
   - **Novelty statement:** bounded, of the form "Among the <N> papers screened, none …", and only as strong as the notes support.
   - **Open questions for the human:** contradictions between notes, claims with weak coverage, papers whose role is unclear.

5. **Update `STATUS.md`:** stage 7 `waiting on human`, date, next action "Human reviews `notes/overview.md`, then runs `/clear` and `/lr-8-draft`".

6. **Report:** notes written, the themes (one line each), the novelty statement, and the open questions.
