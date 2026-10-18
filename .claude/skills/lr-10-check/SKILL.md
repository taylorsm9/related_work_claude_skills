---
name: lr-10-check
description: Stage 10 of the related-work pipeline. Checks every sentence that cites a paper against that paper's PDF and note with one citation-checker subagent per citekey, applies minimal fixes, and writes checks/report.md.
disable-model-invocation: true
---

# Stage 10: Check

**Purpose:** confirm that every citation in the final wording is supported by the cited paper. This runs after humanizer so the wording checked is the wording submitted.

**Reads:** `writing/related_work.tex`; `notes/<citekey>.md`; `library/pdfs/<citekey>.pdf`; `library/refs.bib`.
**Writes:** `checks/<citekey>.json` (via subagents), `checks/report.md`, `writing/related_work.tex` (minimal fixes), `writing/related_work.v3-pre-check.tex`, `STATUS.md`.
**Gate:** the human's final review.

## Steps

1. Read `STATUS.md` and follow the stage-start rule in `CLAUDE.md`: stage 9 must be done (the cite-key comparison passed). Copy `writing/related_work.tex` to `writing/related_work.v3-pre-check.tex`.

2. **Collect citing sentences:** `python3 scripts/cites.py sentences writing/related_work.tex --out checks/sentences.json` maps each citekey to the sentences that cite it, each with the `line` where it starts. Sentences are whitespace-collapsed, so to edit one in the file, go to its line and match ignoring whitespace and line breaks.

3. **Check, one subagent per citekey.** Spawn one `citation-checker` per key, at most about 5 at a time. **Do not pass model or effort.** Give each: `citekey`, its `sentences` (exactly as in `checks/sentences.json`), `note: notes/<citekey>.md`, `pdf: library/pdfs/<citekey>.pdf`, its `bib_entry` (from `python3 scripts/bib.py show <key>`), and `output: checks/<citekey>.json`.

4. **Apply fixes.** For each verdict of `partly`, `unsupported` or `wrong-paper`:
   - If `suggested_fix` is a minimal rewrite that the evidence supports, apply it to `writing/related_work.tex`, changing as little as possible and keeping the surrounding wording and every `\cite{}` command.
   - A `wrong-paper` verdict whose correct paper is not among the kept papers cannot be fixed here: do not add a citation. List it under *Needs your decision*.
   - Where one sentence has verdicts from several checkers, combine the fixes so the sentence stays readable.

5. **Re-verify:** `python3 scripts/cites.py check-bib writing/related_work.tex --bib library/refs.bib`, and `python3 scripts/cites.py compare writing/related_work.v3-pre-check.tex writing/related_work.tex` (any key change must be one you made on purpose and listed).

6. **Write `checks/report.md`** from `templates/check-report.md`: verdict counts, every fix with before and after and its evidence (quote and page), items needing the human's decision, and all `bib_issues`.

7. **Update `STATUS.md`:** stage 10 `waiting on human`, date, next action "Human reviews `checks/report.md` and `writing/related_work.tex`".

8. **Report:** verdict counts, the number of fixes, and anything needing the human's decision. Note that fixes were applied after humanizer; if they were extensive, the human may want to run humanizer once more on the changed sentences and then rerun this stage.
