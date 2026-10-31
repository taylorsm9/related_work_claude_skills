---
name: lr-1-search
description: Stage 1 of the related-work pipeline. Searches arXiv, Semantic Scholar and DBLP from the approved contributions, assesses candidates from abstracts, and writes the list of papers for the human to fetch for the expand stage.
disable-model-invocation: true
---

# Stage 1: Search

**Purpose:** find candidate papers from several engines, judge each against the claims from its abstract, and pick the few the human should fetch so the expand stage can read them in full.

**Reads:** `project/contributions.md` (must be `status: approved`); `templates/schemas.md`.
**Writes:** `research/candidates.jsonl`, `research/abstracts.jsonl`, `research/search-log.md`, `research/assessments/s1-*.json`, `research/candidates.md`, `manual/fetch-for-expand.md`, `STATUS.md`.
**Gate:** the human saves the listed papers, with PDFs, into the project's Zotero collection, which auto-exports to `library/refs.bib`.

## Steps

1. **Check inputs.** Read `STATUS.md` and `project/contributions.md`, and follow the stage-start rule in `CLAUDE.md`: the gate is that the contributions say `status: approved`. If they do not, stop and say so. Run `python3 scripts/candidates.py claims` to confirm the claim IDs. If `research/search-log.md` does not exist, copy it from `templates/search-log.md`.

2. **Write queries.** From each claim's facets, write 2–3 queries (6–12 in total): one with the claim's core technical terms, one with synonyms or the problem phrased differently, and, where useful, one naming the evaluation setting. Keep queries short (3–8 words). Note them in your working notes before running them.

3. **Run searches.** For every query, run each source and add its results. Use `--out` to a scratch file under `research/tmp/`, then add it:
   ```
   python3 scripts/lit.py arxiv-search --query "<q>" --max 25 --out research/tmp/q1-arxiv.json
   python3 scripts/candidates.py add research/tmp/q1-arxiv.json --stage 1 --how arxiv-search --detail "<q>"
   ```
   - `arxiv-search --query "<q>" --max 25`
   - `arxiv-search --query "<q>" --since <date 12 months ago> --sort date --max 25` (recent work, which citation searches miss)
   - `s2-search --query "<q>" --limit 25`, adding `--year <from>-` if the contributions give a year range
   - `dblp-search --query "<q>" --max 25`

   Append one row per search to `research/search-log.md`: date, stage 1, source, query, filters, hits, new candidates (the `add` command prints both counts).

4. **Seeds.** For each paper under *Known related papers*, find it (`s2-match --title "<title>"`, or `s2-paper --id doi:<doi>` / `arxiv:<id>`), check that the returned title really matches, and add it with `--how seed`. Then run `s2-recommend --positive <seed ids…> --limit 50` once and add the results with `--how s2-recommend --detail "<seed ids>"`. Log both.

5. **Fill missing abstracts.** `python3 scripts/candidates.py missing-abstracts > research/tmp/ids.txt`, then `python3 scripts/lit.py s2-batch --ids-file research/tmp/ids.txt --abstract --out research/tmp/abs.json` and `python3 scripts/candidates.py add research/tmp/abs.json --stage 1 --how s2-search --detail "abstract lookup" --abstracts-only`.

6. **Assess.** `python3 scripts/candidates.py make-batches --prefix s1 --size 10` writes `research/assessments/s1-bNN.input.json` files. Spawn one `candidate-assessor` per batch (several in parallel, at most about 5 at a time), each with `batch`, `input` and `output: research/assessments/s1-bNN.json`. **Do not pass model or effort.** When each finishes, run `python3 scripts/candidates.py merge-assessment research/assessments/s1-bNN.json`.

7. **Check and render.** `python3 scripts/candidates.py validate`, then `python3 scripts/candidates.py render`.

8. **Choose papers for expand.** From `python3 scripts/candidates.py list --priority-max 2`, choose **5–8** papers to read in full, preferring:
   - at least one candidate `overlaps` for every claim, where one exists;
   - `closest-prior` and `baseline` roles over `background`;
   - a mix of established and recent papers.
   Mark them with `python3 scripts/candidates.py set <id> status=fetch-for-expand`.

9. **Write `manual/fetch-for-expand.md`** from `templates/fetch-list.md`, as round 1. Use the template's standard *What to do* text. Look up published versions of the chosen papers: write their ids to `research/tmp/round1-ids.txt` (from `python3 scripts/candidates.py list --status fetch-for-expand --json`) and run `python3 scripts/lit.py published-links --ids-file research/tmp/round1-ids.txt --out research/tmp/round1-links.json`. Papers with `extra.published: true` go under *Published version exists*, with `extra.best_link` and the other `extra.links`; the rest go under *On arXiv only*. Link arXiv **abstract pages** (`https://arxiv.org/abs/<id>`, from `ids.arxiv`), never PDF links: Zotero's connector reads the metadata from the abstract page. Never construct an identifier that is not in the record or the lookup. If the lookup fails, list every paper under *On arXiv only* (or with its DOI link if it has no arXiv ID), and say in the report that published versions were not checked.

10. **Update `STATUS.md`:** stage 1 `done`, stage 2 `waiting on human`, date, next action "Human saves the papers in `manual/fetch-for-expand.md` into the Zotero collection, then runs `/lr-3-expand`".

11. **Report** in a few lines: candidates found, per source; how many are priority 1 and 2; the papers chosen for expand and why; any claim with no overlapping candidate (worth the human's own search).

## Notes

- If a source fails (HTTP 429 or network errors), `lit.py` retries with backoff. If it still fails, log the failure in the search log and continue with the other sources; report it at the end.
- Delete `research/tmp/` at the end of the stage.
