---
name: lr-3-expand
description: Stage 3 of the related-work pipeline. Reads every PDF in expand/ with one paper-reader subagent each (including PDFs the human added), updates the candidates from full text, and follows each paper's references and citing papers.
disable-model-invocation: true
---

# Stage 3: Expand

**Purpose:** upgrade judgments from abstract to full text for the papers in `expand/`, identify and judge any PDFs the human added on their own, and grow the candidate list backward (references) and forward (citing papers, recommendations).

**Reads:** `expand/*.pdf`; `research/candidates.jsonl`; `project/contributions.md`; `templates/schemas.md`.
**Writes:** `research/expand/<slug>.json` (via subagents), `research/candidates.jsonl`, `research/assessments/s3-*.json`, `research/search-log.md`, `research/candidates.md`, `STATUS.md`.
**Gate:** none required. The human may add more PDFs to `expand/` and run this stage again.

The main session does not read these PDFs. Each one is read in full by its own `paper-reader` subagent.

## Steps

1. **Inventory.** Read `STATUS.md` and follow the stage-start rule in `CLAUDE.md`: the gate is that stage 1 is done and `expand/` holds at least one PDF (that completes human stage 2). List `expand/*.pdf`, and see which records already point at PDFs with `python3 scripts/candidates.py list --json` (field `pdf`). For each PDF, decide which candidate it belongs to:
   - a candidate whose `pdf` field already names this file, or
   - a `fetch-for-expand` candidate whose title matches the PDF: read **only the first page** (`pages: "1"`) to see the title, then set `pdf` with `python3 scripts/candidates.py set <id> pdf=expand/<file>`;
   - otherwise it is a **manual** PDF: the human added it. Its candidate is `null` for now.
   Skip PDFs that already have a `research/expand/*.json` whose `pdf` field names them (already read in an earlier round), unless the human asked for a re-read.
   If no PDFs are new, stop and say so.

2. **Read, one subagent per PDF.** Spawn one `paper-reader` per new PDF, at most about 5 at a time. **Do not pass model or effort.** Give each:
   - `pdf`: the PDF path
   - `output`: `research/expand/<slug>.json`, using `python3 scripts/candidates.py slug <id>` for known candidates, and `manual-<pdf file name without extension>` for manual PDFs
   - `candidate`: the candidate's full JSON line from `research/candidates.jsonl`, or `null`
   Wait for all of them. If one reports `unreadable` or `unidentified`, note it for the report and continue.

3. **Identify manual PDFs, and PDFs that turned out to be a different paper.** A result counts as manual if it had no candidate, or if the reader reported `identified.matches_candidate: null` for a candidate it was given (the PDF is not that paper). In the second case, first undo the link: `candidates.py set <that candidate's id> pdf=null status=fetch-for-expand`, and tell the human in the report that the right PDF for that paper is still missing.
   For each manual result, look the paper up, writing to a scratch file:
   - `python3 scripts/lit.py s2-paper --id doi:<doi> --abstract --out research/tmp/<name>.json` (or `--id arxiv:<id>`) if `ids_seen` has one;
   - otherwise `python3 scripts/lit.py s2-match --title "<identified.title>" --out research/tmp/<name>.json`.
   Accept a match only if the returned title matches the printed title (the match endpoint always returns its best guess; check `extra.title_similarity`). Then:
   - matched: `python3 scripts/candidates.py add research/tmp/<name>.json --stage 3 --how manual --detail expand/<pdf file> --print-ids`. It prints `new <id>` or `merged <id>`; use that id from here on. Then `candidates.py set <id> pdf=expand/<pdf file>`.
   - not matched: `python3 scripts/candidates.py add-manual --title "<title>" --authors "<authors>" --pdf expand/<pdf file>`, adding `--year <year>` only if the year is known. It prints the new id.
   Rename the expand result to that id's slug (`research/expand/<slug>.json`) so every result is named consistently.
   A manual result with `status: unidentified` cannot be added: leave it, and list the PDF in the report so the human can rename it or add details.

4. **Merge full-text judgments.** For every new result: `python3 scripts/candidates.py merge-expand research/expand/<slug>.json --id <id>`. For results with `status: ok`, this sets `basis: full-text`, the relations, role and `relation_summary`, and `status: expanded`. For `unreadable` or `unidentified` results it records the file but leaves the status, so the paper is still assessed from its abstract in step 7.

5. **Backward: references.** For each result with `status: ok`:
   ```
   python3 scripts/lit.py resolve-refs --expand-file research/expand/<slug>.json --citing-id <id> --out research/tmp/<slug>-refs.json
   python3 scripts/candidates.py add research/tmp/<slug>-refs.json --stage 3 --how reference-of --detail <id>
   ```
   `resolve-refs` matches the reader's `references_of_interest` against Semantic Scholar and keeps each reference's `cited_for` context. List anything it reports as unresolved in your final report; do not invent identifiers for them. Log one search-log row per paper.

6. **Forward: citing papers.** For each expanded paper whose role is `closest-prior` or `baseline`, or that `overlaps` any claim:
   - `python3 scripts/lit.py s2-citations --id <id> --limit 200 --out research/tmp/<slug>-cites.json`. From the output, keep at most **30** per paper: prefer recent papers and those whose citation `contexts` or `intents` show they build on, compare with or extend this paper. Write the kept ones to a new file and add it with `--how cited-by --detail <id>`.
   - Once per stage run, `python3 scripts/lit.py s2-recommend --positive <ids of the expanded papers that overlap a claim> --limit 50`, added with `--how s2-recommend`.
   Log each in the search log. Citation indexes have gaps; this is why the human's manual PDFs matter.

7. **Assess the new candidates.** Fill abstracts as in stage 1 (`candidates.py missing-abstracts`, `lit.py s2-batch … --abstract`, `candidates.py add … --abstracts-only`). Then `python3 scripts/candidates.py make-batches --prefix s3r<round> --size 10`, spawn one `candidate-assessor` per batch (**no model or effort**), and `merge-assessment` each result. Assessments never overwrite a full-text judgment.

8. **Check and render.** `candidates.py validate`, then `candidates.py render`.

9. **Decide whether another round is worth it.** Recommend a second round only if a new candidate looks central: priority 1 and `overlaps` with a claim for which no expanded paper overlaps yet. Mark such papers `status=fetch-for-expand` and append them to `manual/fetch-for-expand.md` under a heading "Round <n+1>". Do not run more than 3 rounds without the human asking.

10. **Update `STATUS.md`:** increment *Expand rounds completed*; stage 3 `done` (or `waiting on human` if a further round is suggested); date; next action: either "Human fetches the round <n+1> papers into `expand/` and reruns `/lr-3-expand`" or "Run `/lr-4-screen`".

11. **Report:** PDFs read (and any unreadable or unidentified), manual PDFs identified, judgments that changed from abstract to full text (especially any that flipped from `overlaps` to `unrelated` or back), new candidates from references and citing papers, unresolved references, and whether another round is suggested.

Delete `research/tmp/` at the end.
