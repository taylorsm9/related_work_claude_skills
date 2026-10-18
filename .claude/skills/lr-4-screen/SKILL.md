---
name: lr-4-screen
description: Stage 4 of the related-work pipeline. Ranks all candidates against the claims and writes research/shortlist.md with a proposed set of at most 20 papers for the human to decide on.
disable-model-invocation: true
---

# Stage 4: Screen

**Purpose:** propose the final set of papers, at most 20, so that every claim is covered by its closest prior work, and let the human decide.

**Reads:** `research/candidates.jsonl`; `research/expand/*.json` (for full-text summaries); `project/contributions.md`.
**Writes:** `research/shortlist.md`; `STATUS.md`.
**Gate:** the human fills the decision column, then runs `/lr-5-fetch`.

This stage needs no subagents: every candidate already has a judgment. Read the data through `scripts/candidates.py list` rather than the raw JSONL, to keep context small.

## Steps

1. Read `STATUS.md` and `project/contributions.md`, and follow the stage-start rule in `CLAUDE.md`: the gate is that stage 3 has run at least once. Run `python3 scripts/candidates.py stats`. If any candidate still has no relations, stop and run stage 3's assessment step for them first.

2. Build the proposal from `python3 scripts/candidates.py list` (all candidates) and the `relation_summary` of expanded papers:
   - **Coverage first.** For every claim, include the paper or papers that overlap with it most closely (`closest-prior`), and any paper the project should compare against (`baseline`). If a claim has no overlapping candidate, say so plainly in the coverage table; that is a finding, not a gap to fill with weaker papers.
   - **Then enabling work** the project builds on directly (methods, datasets, tools it uses).
   - **Background** only to fill out a theme, and only if the total stays at or under 20.
   - **Merge duplicates**: a preprint and its published version are one entry; propose citing the published one.
   - Prefer full-text judgments; mark abstract-only proposals clearly.
   - Propose `keep`, `maybe` (you could not decide; the human must) or `reject` for every candidate with priority 1 or 2. Use `maybe` sparingly: every `maybe` row needs an explicit decision from the human. Lower-priority candidates are rejected by default and listed as a count only.

3. Write `research/shortlist.md` from `templates/shortlist.md`:
   - **Coverage by claim** table.
   - **Proposed set** table, one row per proposed `keep` or `maybe`, ordered by role (closest prior, baseline, enabling, background). Use `overlaps` / `differs` / `—` in the claim columns, the basis, the proposal, an empty **Your decision** cell and a one-line reason.
   - **Proposed rejections** table for rejected priority 1–2 candidates, with reasons, so the human can rescue any.
   - Include each row's `id` in the Paper cell, e.g. `Title (arxiv:2401.01234)`, so stage 5 can match decisions to records.

4. Update `STATUS.md`: stage 4 `waiting on human`, date, next action "Human fills **Your decision** in `research/shortlist.md`, then runs `/lr-5-fetch`".

5. Report: the number proposed to keep, the coverage per claim in one line each, any claim without close prior work, and the papers you were least sure about.
