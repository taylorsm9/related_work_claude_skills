---
name: lr-3-expand
description: Stage 3 of the related-work pipeline. Runs in rounds. Collects the round's PDFs from the Zotero export (and any PDFs dropped in expand/), reads each with one paper-reader subagent, updates the candidates from full text, follows references and citing papers in round 1 only, and lists the next round until every priority 1–2 candidate has been read.
disable-model-invocation: true
---

# Stage 3: Expand

**Purpose:** read in full every candidate that may belong in the section before anything is cut. Round 1 reads the 5–8 papers chosen in stage 1, identifies any papers the human added, and grows the candidate list backward (references) and forward (citing papers, recommendations). Later rounds read every remaining priority 1–2 candidate. Every paper read in full at priority 1–2 goes forward to the synthesis (stage 5), which decides what the section cites. Later rounds do not search for new papers: the list grown in round 1 is enough for a short related-work section, and reviewers can point out anything important that was missed.

**Reads:** `library/refs.bib` (the Better BibTeX export of the project's Zotero collection, with PDF paths); `expand/*.pdf`; `research/candidates.jsonl`; `manual/fetch-for-expand.md`; `project/contributions.md`; `templates/schemas.md`; `templates/fetch-list.md`.
**Writes:** `expand/<slug>.pdf` (copies from Zotero), `research/expand/<slug>.json` (via subagents), `research/candidates.jsonl`, `research/assessments/s3r*-*.json`, `research/search-log.md`, `research/candidates.md`, `manual/fetch-for-expand.md`, `STATUS.md`.
**Gate:** after each round that lists a next one, the human saves those papers into Zotero and reruns this stage. When no round is left, continue to `/lr-4-intake`.

The main session does not read these PDFs. Each one is read in full by its own `paper-reader` subagent. This round's number is *Expand rounds completed* in `STATUS.md` plus 1.

## Steps

1. **Collect and inventory.** Read `STATUS.md` and follow the stage-start rule in `CLAUDE.md`: the gate is that stage 1 is done and the human has saved the round's papers (`library/refs.bib` exists) or put PDFs in `expand/` (that completes human stage 2).
   - **From Zotero.** If `library/refs.bib` exists, run `python3 scripts/candidates.py collect-pdfs`. It copies the PDF of every `fetch-for-expand` candidate found in the export to `expand/<slug>.pdf` and sets its `pdf` field. Note for the report the papers it lists as `not in Zotero` or `no PDF in Zotero`, and any `conflict`. If listed papers are in Zotero but none has a PDF, the export probably lacks attachment paths: stop and ask the human to check that Better BibTeX exports the `file` field.
   - **Papers the human added in Zotero.** Entries listed as `no candidate` that have a PDF: copy each with `python3 scripts/bib.py pdf <key> --copy-to expand/zotero-<key>.pdf`. They are manual PDFs (below).
   - **All PDFs.** List `expand/*.pdf`, and see which records already point at PDFs with `python3 scripts/candidates.py list --json` (field `pdf`). For each PDF, decide which candidate it belongs to:
     - a candidate whose `pdf` field already names this file, or
     - a `fetch-for-expand` candidate whose title matches the PDF: read **only the first page** (`pages: "1"`) to see the title, then set `pdf` with `python3 scripts/candidates.py set <id> pdf=expand/<file>`;
     - otherwise it is a **manual** PDF: the human added it. Its candidate is `null` for now.
   Skip PDFs that already have a `research/expand/*.json` whose `pdf` field names them (already read in an earlier round), unless the human asked for a re-read.
   If no PDFs are new, stop and say so.

2. **Read, one subagent per PDF.** Spawn one `paper-reader` per new PDF, at most about 5 at a time; later rounds can hold dozens of papers, so keep starting new readers as earlier ones finish. **Do not pass model or effort.** Give each:
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

5. **Backward: references (round 1 only).** Skip this step in later rounds, even for papers that overlap a claim. In round 1, for each result with `status: ok`:
   ```
   python3 scripts/lit.py resolve-refs --expand-file research/expand/<slug>.json --citing-id <id> --out research/tmp/<slug>-refs.json
   python3 scripts/candidates.py add research/tmp/<slug>-refs.json --stage 3 --how reference-of --detail <id>
   ```
   `resolve-refs` matches the reader's `references_of_interest` against Semantic Scholar and keeps each reference's `cited_for` context. List anything it reports as unresolved in your final report; do not invent identifiers for them. Log one search-log row per paper.

6. **Forward: citing papers (round 1 only).** Skip this step in later rounds. In round 1, for each paper read whose role is `closest-prior` or `baseline`, or that `overlaps` any claim:
   - `python3 scripts/lit.py s2-citations --id <id> --limit 200 --out research/tmp/<slug>-cites.json`. From the output, keep at most **30** per paper: prefer recent papers and those whose citation `contexts` or `intents` show they build on, compare with or extend this paper. Write the kept ones to a new file and add it with `--how cited-by --detail <id>`.
   - `python3 scripts/lit.py s2-recommend --positive <ids of the expanded papers that overlap a claim> --limit 50`, added with `--how s2-recommend`.
   Log each in the search log. Citation indexes have gaps; this is why the human's own additions matter.

7. **Assess the new candidates.** Fill abstracts as in stage 1 (`candidates.py missing-abstracts`, `lit.py s2-batch … --abstract`, `candidates.py add … --abstracts-only`). Then `python3 scripts/candidates.py make-batches --prefix s3r<round> --size 10`, spawn one `candidate-assessor` per batch (**no model or effort**), and `merge-assessment` each result. Assessments never overwrite a full-text judgment. In later rounds the only new candidates are papers added in step 3 that could not be read; `make-batches` prints `nothing to assess` when there are none.

8. **Check and render.** `candidates.py validate`, then `candidates.py render`.

9. **Plan the next round.** Every candidate at priority 1–2 is read in full before intake. The next round is every priority 1–2 candidate with status `candidate` and no PDF (`python3 scripts/candidates.py list --priority-max 2 --missing-pdf --json`), leaving out any whose `decision_reason` says the PDF is not available. After round 1 that is most of the priority 1–2 list. Later rounds add no papers from searches, so after round 2 this list is normally empty, and a next round holds only papers still missing from earlier rounds (below). If both are empty, there is no next round.
   Otherwise, mark each `status=fetch-for-expand` and append to `manual/fetch-for-expand.md` a section `## Round <n+1>` in the format of `templates/fetch-list.md`, with the standard *What to do* text:
   - Write the round's ids to `research/tmp/next-ids.txt` and run `python3 scripts/lit.py published-links --ids-file research/tmp/next-ids.txt --out research/tmp/next-links.json`.
   - Papers with `extra.published: true` go under *Published version exists*, with `extra.best_link` and the other `extra.links`, or "no link found" and the venue. The rest go under *On arXiv only*, linked by their arXiv **abstract page**, never the PDF.
   - Order each list by priority, then by how close the paper is to the claims, and give each a one-line *Why* from its record.
   - Papers from earlier rounds that are still `fetch-for-expand` without a PDF go under a third heading, *Still missing from earlier rounds*. If the human says a paper's PDF cannot be had, set `status=candidate decision_reason="PDF not available (human, <date>)"`; it is then left out of the synthesis, and intake lists it.
   If the lookup fails, list every paper under *On arXiv only* (or with its DOI link if it has no arXiv ID) and say in the report that published versions were not checked. Do not plan more than 3 rounds without the human asking; if the limit is reached, list what the next round would contain in the report instead.

10. **Update `STATUS.md`:** increment *Expand rounds completed*. If a next round is listed: stage 3 `waiting on human`, date, next action "Human saves the round <n+1> papers in `manual/fetch-for-expand.md` into the Zotero collection, then reruns `/lr-3-expand`". Otherwise: stage 3 `done`, date, next action "Run `/lr-4-intake`".

11. **Report:** PDFs read (and any unreadable or unidentified); listed papers not in Zotero or without a PDF; papers the human added; judgments that changed from abstract to full text (especially any that flipped between `overlaps` and `unrelated`); in round 1, new candidates from references and citing papers and any unresolved references; and the next round's size (arXiv only / published version / still missing), or that the stage is done.

Delete `research/tmp/` at the end.
