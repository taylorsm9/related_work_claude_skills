---
name: lr-7-draft
description: Stage 7 of the related-work pipeline. Drafts writing/related_work.tex from the synthesis (notes/synthesis.md) and the per-paper notes and summaries, citing only keys in library/refs.bib. Run in a fresh session.
disable-model-invocation: true
---

# Stage 7: Draft

**Purpose:** write the related-work section: a map of the work around ours, in which papers are related to one another rather than listed one by one.

**Reads:**
- `project/contributions.md` (claims, scope, target length) and the paper draft in `project/`: abstract, method and experiments. Our side of every comparison comes from the draft.
- `notes/synthesis.md` (see *Using the synthesis*).
- `notes/<citekey>.md` for every paper under *Papers to cite* (evidence notes; their *Caveats* are binding).
- As needed: `notes/summaries/<citekey>.md` (claim-free summaries), `notes/ours-summary.md`, `notes/field-taxonomy.md`, `notes/synthesis-map.md`.
- `library/refs.bib` (keys only).

**Writes:** `writing/related_work.tex`, `writing/related_work.v1-draft.tex`, `STATUS.md`; `research/candidates.jsonl` only to record papers cut for fit.

**Start in a fresh session.** If this conversation already contains earlier stages, tell the human to run `/clear` and invoke `/lr-7-draft` again, and stop. The search history should not shape the prose.

## Using the synthesis

The synthesis stage has already done the analysis: how the field groups its papers, how the papers relate, where ours sits, which papers to cite, and what must not be claimed. Use that analysis, but do not reproduce its format.

**Binding on the draft:**
- **Positioning corrections.** Each names a paper that is closer to ours than the expand-stage judgment assumed, and the difference to state. The section must discuss every one and acknowledge what it shares with ours. The stated difference is a suggestion: include it where it helps the reader, and cut it where it does not.
- **Do not say**, and each cited paper's note *Caveats*. Hard limits on what the section may claim. Where a note's caveat says its paper does not support something the synthesis planned, the note wins: it was written later, from the full PDF.
- **Known weaknesses.** Read them before writing about the areas they name. Where coverage may have gaps (*Possibly missing papers*), do not write "no prior work" or "no existing method" about that area.

**Papers to cite.** Cite these papers. You may drop one that does not fit the section you write, except a positioning-correction paper; list every paper dropped in the report.

**Source material, to use as you see fit:**
- *Groups*, *Cross-paper statements available* and *Crossovers and new categories* give each group's defining property and the relations between papers, with evidence. They are the raw material for sentences about several papers at once.
- *Organization*, *Paragraph plan* and *Order and arc* show one worked-out arrangement of the section, with the reasoning behind it. Treat it as a suggestion. The number of paragraphs, their order, what each covers and how each is built are your choice, and you may find a better arc once you start writing. You are not bound to its planned sentences, its per-paragraph word counts, or its pattern of topic sentence, synthesis sentence, closing contrast and transition.

The synthesis points to its evidence: `S12` is evidence item 12 in that paper's summary, plus expand-stage quotes, map columns and `notes/synthesis-verify/` files. Each cited paper's note (`E5` is its item 5) was written afterwards and checks the plan's statements about that paper. Open the note, or the summary, behind a sentence when you write that sentence. Do not load every summary.

## Writing

**What good looks like.** This is guidance, not a template.
- Write about groups and how they relate. One sentence that relates several papers (a shared property, a contrast, a lineage, two lines converging) says more than several sentences that each describe one paper. Avoid long runs of single-paper sentences.
- Use the field's own names for its categories (from `notes/field-taxonomy.md`) where they fit, so readers recognize them.
- Let the content decide each paragraph's shape. Do not build every paragraph the same way.

**Rules:**
- LaTeX only: `\section{Related Work}` (or the heading the draft uses), then the paragraphs. No Markdown.
- Cite with `\cite{key}` (or the command the draft uses). Every key must be in `library/refs.bib` and be a paper listed under *Papers to cite*.
- Every statement about a paper must be supported by evidence for that paper: its note, its summary, a verify result or a taxonomy quote. Statements about our paper come from the draft. Do not add facts, numbers or characterizations that none of these contain.
- Keep to the length and citation requirements in *Target section* of `project/contributions.md`. The number of paragraphs is up to you.
- Never write "first" or "only" in a broader form than the synthesis's *Do not say* allows.
- Give prior work the credit it is due, including where it got there first, and do not disparage it.

## Steps

1. Read `STATUS.md` and follow the stage-start rule in `CLAUDE.md`. The gate is that stage 6 is done: `notes/synthesis.md` exists with a review status at its top, and every paper under *Papers to cite* has a note. Mark the stages before this one `done`. Read `project/contributions.md`, the draft's abstract, method and experiments, and `notes/synthesis.md` in full, and the *Caveats* of every cited paper's note.

2. **Plan, briefly, in the conversation.** The plan is not a deliverable. Decide the arc of the section. For each part, list the papers, what you will say about them, and where the support is. Check that the plan handles every positioning correction and cites every paper *Target section* requires.

3. **Write `writing/related_work.tex`** following *Writing*.

4. **Check the draft against the binding items.** Go through *Do not say*, the cited notes' *Caveats* and the positioning corrections one at a time, and read every sentence that claims a difference or a novelty against them. Run `python3 scripts/cites.py keys writing/related_work.tex` and confirm that every key is listed under *Papers to cite*, and that every positioning-correction paper is cited.

5. **Check keys:** `python3 scripts/cites.py check-bib writing/related_work.tex --bib library/refs.bib`. Fix any missing key; do not add BibTeX entries yourself.

6. Copy the file to `writing/related_work.v1-draft.tex` (a saved version for comparison later).

7. **Record papers cut for fit:** for each paper under *Papers to cite* that the draft does not cite, `python3 scripts/candidates.py set <id> status=reject decision_reason="cut for fit in the draft: <reason>"`, then `python3 scripts/candidates.py validate`.

8. **Update `STATUS.md`:** stage 7 `done`, the date, and next action "Run `/lr-8-humanize`".

9. **Report:**
   - the section's arc, one line per paragraph;
   - the word count and the number of distinct papers cited;
   - how each positioning correction was handled;
   - the main departures from the synthesis's paragraph plan, and why;
   - the papers under *Papers to cite* that were cut, and why.
