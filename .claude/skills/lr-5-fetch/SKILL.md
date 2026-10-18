---
name: lr-5-fetch
description: Stage 5 of the related-work pipeline. Applies the human's shortlist decisions and writes the final fetch list containing only kept papers whose PDFs are not already in expand/, plus the Zotero export instructions.
disable-model-invocation: true
---

# Stage 5: Fetch the rest

**Purpose:** record the final decisions and tell the human exactly what is left to fetch, so no paper is fetched twice.

**Reads:** `research/shortlist.md` (with the human's decisions); `research/candidates.jsonl`.
**Writes:** `research/candidates.jsonl` (statuses), `manual/fetch-final.md`, `STATUS.md`.
**Gate:** the human puts the PDFs in `library/inbox/` and exports the Zotero collection to `library/refs.bib`, then runs `/lr-6-intake`.

## Steps

1. **Check the gate first.** Read `STATUS.md` and follow the stage-start rule in `CLAUDE.md`. For every row in `research/shortlist.md`, the decision is the **Your decision** cell if filled, otherwise the proposal. If any row's decision is still `maybe`, list those rows, ask the human to decide them, and stop **before changing anything**. If more than 20 papers would be kept, tell the human and ask whether to continue; do not drop any yourself.

   **Then apply decisions.** Set each record: `python3 scripts/candidates.py set <id> status=<keep|reject> decision_reason="<reason>"`. Candidates not listed in the shortlist become `reject` with reason "not shortlisted (priority 3–4)" (find them with `candidates.py list`; skip records already `keep` or `reject`).

2. **Validate:** `python3 scripts/candidates.py validate`.

3. **Write `manual/fetch-final.md`** from `templates/fetch-list.md`, listing kept papers **whose `pdf` is null** (not already in `expand/`): `python3 scripts/candidates.py list --status keep --missing-pdf --json` gives them with their `ids` for the links. `list --status keep --json` gives all kept papers for the final section. Replace *What to do* with:
   > 1. In Zotero, create a collection for this paper and add **every kept paper**, including the ones already in `expand/` (all <n> are listed at the end). Adding by identifier works with the arXiv IDs and DOIs below. Prefer the published version where one exists.
   > 2. With Better BibTeX, right-click the collection → *Export Collection…* → format *Better BibTeX*, tick *Keep updated*, and save as `library/refs.bib` in this repository.
   > 3. Download the PDFs listed under *Papers* into `library/inbox/` (any filenames). The ones already in `expand/` do not need fetching again.
   > 4. Run `/lr-6-intake`.

   After the *Papers* section, add a section **All kept papers (for the Zotero collection)** listing every kept paper's title with its arXiv ID or DOI.

4. **Update `STATUS.md`:** stage 5 `waiting on human`, date, next action "Human fetches the PDFs in `manual/fetch-final.md` into `library/inbox/`, exports the Zotero collection to `library/refs.bib`, then runs `/lr-6-intake`".

5. **Report:** papers kept, how many still need fetching, and the reminder to export the whole collection (not just the newly fetched papers) to `library/refs.bib`.
