---
name: lr-0-contributions
description: Stage 0 of the related-work pipeline. Drafts project/contributions.md (the numbered claims every later stage judges papers against) from the paper draft in project/.
disable-model-invocation: true
---

# Stage 0: Contributions

**Purpose:** turn the paper draft into 3–5 numbered, checkable claims (C1, C2, …) with facets. Every later stage scores papers against these claims, so their quality decides the quality of the search.

**Reads:** everything in `project/` except `README.md`; `templates/contributions.md`.
**Writes:** `project/contributions.md`; `STATUS.md`.
**Gate:** the human edits the file and sets `status: approved`.

## Steps

1. Read `STATUS.md` and follow the stage-start rule in `CLAUDE.md` (stage 0 has no gate before it). If `project/contributions.md` already exists with `status: approved`, stop and tell the human stage 0 is done; suggest `/lr-1-search`.
2. Find the draft in `project/` (`.tex`, `.md`, `.txt` or `.pdf`). If there is none, stop and ask the human to add one. For a PDF, read it in chunks of up to 20 pages.
3. Copy `templates/contributions.md` to `project/contributions.md` (or update the existing draft) and fill it in:
   - **The paper in one paragraph:** what was built or run, on what, and what it showed.
   - **Claims:** 3–5 claims of what is new, each one sentence, specific enough that a prior paper could be shown to overlap with it. Prefer the paper's own stated contributions. Split compound claims. For each, fill the facets: problem, method or mechanism, evaluation, and what would count as overlap.
   - **Known related papers:** papers the draft already cites or names as baselines, with arXiv IDs or DOIs only if they appear in the draft. These become seeds for stage 1.
   - **Scope:** field, years, and anything that looks related but is out of scope, if the draft makes it clear.
   - **Target section:** venue and length if known; otherwise "2–4 paragraphs, about 400 words".
   Leave `status: draft`.
4. Where the draft is ambiguous (for example, it is unclear whether something is a contribution or prior work), write the question as an HTML comment next to the claim instead of guessing.
5. Update `STATUS.md`: stage 0 `waiting on human`, today's date, next action "Human edits `project/contributions.md` and sets `status: approved`, then runs `/lr-1-search`".
6. Tell the human: the claims you drafted (one line each), any questions you left in comments, and that they should edit the file and set `status: approved` before running `/lr-1-search`.
