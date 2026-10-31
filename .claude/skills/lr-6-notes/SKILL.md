---
name: lr-6-notes
description: Stage 6 of the related-work pipeline. Writes one evidence note per paper the synthesis chose to cite, with note-writer subagents, and checks each note against what the synthesis plans to say about that paper.
disable-model-invocation: true
---

# Stage 6: Notes

**Purpose:** produce the evidence the section is drafted from: one note per cited paper, with quoted evidence, written after the synthesis so that every statement the plan makes about a paper is checked against its PDF.

**Reads:** records with status `keep` in `research/candidates.jsonl` (the papers the synthesis chose); `library/pdfs/<citekey>.pdf`; `research/expand/<slug>.json`; `notes/synthesis.md`; `project/contributions.md`; `templates/note.md`.
**Writes:** `notes/<citekey>.md` (via subagents), `STATUS.md`.
**Gate:** none.

## Steps

1. Read `STATUS.md` and follow the stage-start rule in `CLAUDE.md`: the gate is that stage 5 is done, `notes/synthesis.md` exists, and every paper with status `keep` has a citekey and a PDF in `library/pdfs/` (check with `candidates.py list --status keep`, last column, and the files).

2. **Notes, one subagent per paper.** For each paper with status `keep` without a `notes/<citekey>.md`, spawn one `note-writer`, at most about 5 at a time. **Do not pass model or effort.** Give each: `citekey`, the paper's JSON line from `research/candidates.jsonl`, `pdf: library/pdfs/<citekey>.pdf`, `expand_file` (the record's `expand_file`, or `null`), `synthesis: notes/synthesis.md`, and `output: notes/<citekey>.md`. Wait for all of them.

3. **Check the notes** without reading the PDFs: every note has every section of `templates/note.md`, a verdict for every claim, and at least one numbered evidence quote with a page. Re-spawn the `note-writer` for any note that does not.

4. **Update `STATUS.md`:** stage 6 `done`, date, next action "Run `/clear`, then `/lr-7-draft`".

5. **Report:** notes written, and every statement in `notes/synthesis.md` that a note's *Caveats* says its paper does not support (paper, statement, what the paper says instead). The draft treats those caveats as binding.
