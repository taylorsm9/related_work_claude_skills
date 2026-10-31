---
name: lr-8-humanize
description: Stage 8 of the related-work pipeline. Runs the humanizer skill on writing/related_work.tex to remove AI writing patterns, then verifies that every citation key and the LaTeX survived unchanged.
disable-model-invocation: true
---

# Stage 8: Humanize

**Purpose:** edit the draft's prose with humanizer, without changing what it claims or which papers it cites.

**Reads / writes:** `writing/related_work.tex`; saves `writing/related_work.v2-pre-humanizer.tex`; `STATUS.md`.
**Requires:** the humanizer plugin (https://github.com/blader/humanizer). If it is not installed, stop and tell the human to run `/plugin marketplace add blader/humanizer` and `/plugin install humanizer@humanizer`.

## Steps

1. Read `STATUS.md` and follow the stage-start rule in `CLAUDE.md`: the gate is that stage 7 is done and `writing/related_work.tex` exists. Copy `writing/related_work.tex` to `writing/related_work.v2-pre-humanizer.tex`.

2. **Run humanizer** on `writing/related_work.tex` (use the humanizer skill; as a plugin it is `/humanizer:humanizer`). Give it the file path so it edits only the prose, and these constraints:
   - Keep every `\cite{…}` command exactly as it is, attached to the same claim.
   - Keep all LaTeX intact: commands, environments, `%` comments, math. Do not convert to Markdown.
   - Do not change what any sentence says a paper did or found, or how the project is said to differ. Wording may change; claims may not.

3. **Verify citations:** `python3 scripts/cites.py compare writing/related_work.v2-pre-humanizer.tex writing/related_work.tex`. It must report the same keys with the same counts. If any key was lost, moved to a different claim, or duplicated, restore the citation by hand in the edited file and run the comparison again.

4. **Verify claims.** Read the two versions side by side, sentence by sentence. For any sentence whose claim about a paper changed (not just its wording), restore the claim from the pre-humanizer version while keeping humanizer's wording where possible. List every such repair.

5. Run `python3 scripts/cites.py check-bib writing/related_work.tex --bib library/refs.bib`.

6. **Update `STATUS.md`:** stage 8 `done`, date, next action "Run `/lr-9-check`".

7. Report: the cite-key comparison result, any repairs, and the word count before and after.
