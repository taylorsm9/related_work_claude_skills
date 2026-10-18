---
name: lr-8-draft
description: Stage 8 of the related-work pipeline. Drafts writing/related_work.tex from notes/overview.md and the per-paper notes, citing only keys in library/refs.bib. Run in a fresh session.
disable-model-invocation: true
---

# Stage 8: Draft

**Purpose:** write the related-work section from the notes, and nothing else.

**Reads:** `project/contributions.md`; the paper draft in `project/` (abstract and method); `notes/overview.md`; `notes/<citekey>.md` as needed; `library/refs.bib` (keys only).
**Writes:** `writing/related_work.tex`, `writing/related_work.v1-draft.tex`, `STATUS.md`.

**Start in a fresh session.** If this conversation already contains earlier stages, tell the human to run `/clear` and invoke `/lr-8-draft` again, and stop. The search history should not shape the prose.

## Steps

1. Read `STATUS.md` and follow the stage-start rule in `CLAUDE.md`: the gate is that `notes/overview.md` exists. The human running this stage means they have reviewed it, so mark stage 7 `done`. Read `project/contributions.md`, the abstract and method of the draft, and `notes/overview.md`.

2. **Plan before writing.** One paragraph per theme in the overview, in an order that leads to the project's contributions (usually the broadest theme first, the closest prior work last). For each paragraph, list the citekeys and the statements you will make, each taken from a note's *Statements we can make* or *Evidence*. Open a note whenever a statement needs it.

3. **Write `writing/related_work.tex`:**
   - `\section{Related Work}` (or the heading the draft uses), then the paragraphs. LaTeX only: no Markdown.
   - Cite with `\cite{key}` (or the citation command the draft uses), using only keys in `library/refs.bib` that have a note in `notes/`.
   - Every statement about a paper must be supported by that paper's note. Do not add facts, numbers or characterizations that the notes do not contain.
   - Each paragraph ends with how the project differs from that group, consistent with *Closest prior work per claim* in the overview. State differences precisely and without disparaging prior work.
   - Use the novelty statement's bounded form; never claim to be "the first" unless the overview's novelty statement supports exactly that.
   - Keep to the length in *Target section* of `project/contributions.md`.

4. **Check keys:** `python3 scripts/cites.py check-bib writing/related_work.tex --bib library/refs.bib`. Fix any missing key; do not add BibTeX entries yourself.

5. Copy the file to `writing/related_work.v1-draft.tex` (a saved version for comparison later).

6. **Update `STATUS.md`:** stage 8 `done`, date, next action "Run `/lr-9-humanize`".

7. Report the paragraph plan (one line per paragraph) and the word count.
