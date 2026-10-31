---
name: lr-5-synthesize
description: Stage 5 of the related-work pipeline, run after intake and before notes. Over every paper read in full, learns how the field organizes itself from the papers' own related-work sections, writes claim-free summaries guided by that, builds a comparison table, places our paper in it, revisits the categories, writes a paragraph plan to notes/synthesis.md, and chooses the papers the section cites. Fully automatic; a fresh-context reviewer replaces human review.
disable-model-invocation: true
---

# Stage 5: Synthesize

**Purpose.** A related-work section is judged by its synthesis: what it says about *groups* of papers, how they relate to one another, and where our work sits among them. The expand-stage judgments describe each paper against our claims, one at a time. That is necessary but not enough, and organizing the section by our claims is often not the most sensible structure. This stage builds the structure from the literature itself, starting with the strongest evidence available about how the field divides up: the related-work sections the papers' own authors wrote. Then it positions our paper within that structure, and chooses which papers the section cites.

Two failure modes this stage exists to prevent:
1. **A list instead of a synthesis**: one summary per paper, strung together.
2. **Claim-shaped blindness**: a paper that closely resembles ours (for example, one that performs the same *combination* of operations) is missed, or a natural category of papers goes unseen, because no claim asked about that combination.

**Order of work, and why.** First extract every paper's related-work section, then read them all together to learn the field's categories and the distinctions it draws. Only then summarize each paper, because the taxonomy tells the summaries what to look for. Then build the table from the taxonomy and the summaries. Our claims enter only after the table exists.

**The synthesis set** is every paper intake gave a citekey: `python3 scripts/candidates.py list --has-citekey --json`. These are the papers read in full at priority 1–2. Nothing has been cut from them; this stage decides which ones the section cites.

**Reads:** `library/pdfs/<citekey>.pdf` (through subagents only); the paper draft in `project/`; `project/contributions.md`; the set's records and their expand-stage judgments, `research/expand/<slug>.json` (each record's `expand_file`).
**Writes:**
- `notes/field/papers.md`, `notes/field/<citekey>-related.md` (related-work extractions) and `notes/field/digest.md`
- `notes/field-taxonomy.md`
- `notes/summaries/<citekey>.md`, `notes/summaries-digest.md`, and `notes/ours-summary.md` (kept outside `notes/summaries/`, which the blind mapper reads)
- `notes/synthesis-map.md`
- `notes/synthesis-verify/<citekey>-<n>.json` (one file per property checked)
- `notes/synthesis.md`
- `notes/synthesis-review.md`
- `research/candidates.jsonl` (`status` and `decision_reason` of the set, at the end), `STATUS.md`

**Place in the pipeline:** after intake (4), before notes (6). **Entry gate:** stage 4 is done: every paper in the set has a citekey and a PDF in `library/pdfs/`.
**Exit gate:** none. The stage finishes on its own. The notes stage then writes a note for each paper chosen here, and drafting uses `notes/synthesis.md`, with the paragraph plan as a suggestion and the positioning corrections, *Do not say* and *Known weaknesses* as binding.

Spawn subagents by name and **do not pass model or effort**. Run per-paper subagents in parallel, at most about 5 at a time.

**When a check fails twice:** every "re-spawn once" below means exactly once. If the second attempt also fails, continue with what you have and record the gap under *Known weaknesses* in `notes/synthesis.md`. Never stop to ask a human.

## Steps

### 1. Check inputs
Read `STATUS.md` and follow the stage-start rule in `CLAUDE.md`, using the entry gate above. List the set: `python3 scripts/candidates.py list --has-citekey --json`. Every paper needs `library/pdfs/<citekey>.pdf`; if any is missing, stop and say which.

Write `notes/field/papers.md`: one line per paper in the set with citekey, title and year, taken from the records. This list contains no information about our project; the taxonomy builder uses it to recognize papers in the set when other papers cite them.

### 2. Extract each paper's related-work section
Spawn one `related-work-extractor` per paper with `citekey`, `pdf`, and `output: notes/field/<citekey>-related.md`. When all have finished, check that every output exists and has a *Structure* section. Re-spawn once for any that does not. A paper with no discussion of prior work at all is fine; its output says so.

Then build the digest the taxonomy builder reads first (mechanical, no judgment):
`python3 scripts/digest.py --title "Digest of related-work extractions" --section Structure --section "Positioning sentences" --out notes/field/digest.md notes/field/*-related.md`

### 3. Build the field taxonomy
Spawn one `taxonomy-builder` with `notes/field/digest.md`, every `notes/field/*-related.md`, `notes/field/papers.md`, and `output: notes/field-taxonomy.md`. Check that it has at least one category and a **Distinctions** table; if not, re-spawn once with the problem stated.

### 4. Summarize each paper, guided by the taxonomy
Spawn one `paper-summarizer` per paper with `citekey`, `pdf`, and `output: notes/summaries/<citekey>.md`. Each reads `notes/field-taxonomy.md` and answers its distinctions for the paper, and also records what the taxonomy does not capture. Check that every summary answers every distinction (`not stated` counts as an answer); re-spawn once for any that does not.

Then build the digest the mapper reads first:
`python3 scripts/digest.py --title "Digest of paper summaries" --section "Short description for writing" --section "Method, step by step" --section "Distinctions from the field taxonomy" --section "Not captured by the taxonomy" --section "Where the field places it" --out notes/summaries-digest.md notes/summaries/*.md`

### 5. Build the table
Spawn one `literature-mapper` in **map mode** with the set's citekeys, `notes/field-taxonomy.md`, `notes/summaries-digest.md`, the summaries, and `output: notes/synthesis-map.md`.

When it finishes, check the map's structure, not its judgments:
- every paper in the set has a row;
- there is an Option A (the field's organization) and at least one other option;
- every paper is placed in every option or listed under *Fits two groups or none*.

If any check fails, spawn it once more with the specific problems listed.

### 6. Add our paper to the table
Create `notes/synthesis.md` from `templates/synthesis.md` now. Steps 6–8 fill its first sections, and step 10 fills the rest.

Read the paper draft (abstract, method and experiments), **not** `contributions.md` yet. Write `notes/ours-summary.md` in the same format as the other summaries (`templates/paper-summary.md`), answering the same distinctions. Then fill our row in `notes/synthesis.md` using the map's columns. Use `?` where the draft does not say.

If our method performs an operation, or a joint pairing of operations, that has no column, add the column. Fill it for every paper from its summary, in the *Added columns* table of `notes/synthesis.md`. Where a summary does not say, spawn `literature-mapper` in **verify mode** (citekey, the property as one sentence, the PDF, `output: notes/synthesis-verify/<citekey>-<n>.json`, numbering each property checked for that paper) rather than guessing.

### 7. Revisit the categories
Before choosing an organization, step back from the matrix, with our row included, and from the field taxonomy. Look at where papers cross over: rows that combine operations other papers do separately, papers the field places in two categories, columns where papers from different groups agree, combinations only one or two papers have. Ask whether any of these suggest a category the map's options missed — for example, a group defined by doing two things at once, rather than by either one. Ask, too, which crossovers the field already names (in the taxonomy's *Combinations*) and which it does not. You don't have to change anything. Write down the crossovers you notice, any categories they suggest, and whether you adopt them and why.

Then read `contributions.md`, and the expand-stage judgments of the set: each record's `role` and `relation_summary` (`candidates.py list --has-citekey --json`), and, where you need the detail, the per-claim `relations` with their quotes in its `research/expand/<slug>.json`. Note any paper that does something close to what ours does that the expand-stage judgment did not treat as close (role `closest-prior`, or `overlaps` for a claim). Check the taxonomy's *How papers position themselves*: if a paper in the set claims the same difference our paper claims, note it.

Write all of this under **Crossovers and new categories** in `notes/synthesis.md`.

### 8. Confirm anything new before relying on it
For every paper noted in step 7 as close to ours but not treated so in the expand-stage judgments, and every paper that claims the same difference ours does, state what it shares with ours in one sentence. Confirm it from the paper's summary evidence if it is there, otherwise with `literature-mapper` in verify mode (`output: notes/synthesis-verify/<citekey>-<n>.json`). If confirmed (`yes` or `partly`), write a **positioning correction**: the section must compare this paper with ours and state the precise difference, taken from the two summaries and the evidence. If not confirmed, record that it was checked and why it is not close.

Positioning corrections are binding on the draft. Do not edit the expand files.

### 9. Choose the organization
Consider the map's options (Option A is the field's own organization), any categories adopted in step 7, and organizing by our claims as one more option, never as the default. You may adapt an option (merge, split or rename groups) if you say why. Prefer the organization where:
1. each group has a **defining property true of every member**, statable in one sentence;
2. **every paper in the set is placed**, with a justification from its row, and placements agree with how the field places papers, or say why they differ;
3. groups **contrast with each other** on a named dimension, so the section reads as a map of the field;
4. the section can **end at the work closest to ours**, including any paper from the positioning corrections, so the last paragraph sets up our contribution;
5. it tells a story a reader in the field would recognize: a line of ideas, or two lines of work converging (see the map's *Observations* and your crossovers).

Departing from the field's organization is allowed, and sometimes right, but say why: readers and reviewers know the field's categories. Use the field's names for groups wherever they fit.

A paper that fits two groups because it combines them is not a flaw. It often belongs where the two groups meet, as the transition between their paragraphs, or in the closing paragraph if it is close to ours.

Record the choice and why each alternative lost.

### 10. Write the synthesis, the paragraph plan and the papers to cite
Fill the remaining sections of `notes/synthesis.md`, keeping the sections steps 6–9 already wrote.

**Groups.** For each group: its defining property; its members, with justifications; how the members differ from one another (use the map's relations: `builds-on`, `competes`, `combines`, `contradicts` …); and how ours relates.

**Cross-paper statements available.** Statements that relate two or more papers, each with its evidence: summary evidence numbers, taxonomy quotes, or verify results. These are what turn a list into a synthesis. Useful forms:
- *shared property*: several papers have a property the rest of the field lacks;
- *contrast within a group*: how two members of one group differ;
- *lineage*: one paper extends another's method;
- *convergence*: two lines of work meet in one paper that does both.

**Paragraph plan.** One paragraph per group (or per role, for the closing paragraph), sized to the target length in `contributions.md`. For each paragraph:
- a **topic sentence that makes a claim about the group**, not about one paper, in the field's terms;
- at least one **synthesis sentence relating two or more papers**, with support;
- the papers and the role each plays in the paragraph (cited for the shared property, contrasted, extended …);
- a **closing contrast with our work**: the precise difference, from *Groups* or *Positioning corrections*, stated without disparaging prior work;
- a transition to the next paragraph.

Avoid plans where more than two consecutive sentences each describe a single paper. Prefer citing several papers in one sentence when they share a property.

**Papers to cite.** Choose, on your own judgment, the papers the section cites; no human reviews the choice. Include every paper the paragraph plan relies on: each positioning-correction paper, the work closest to ours, and, for each group, enough members to support its group sentences (a group with one cited member is not a line of work). Keep to *Target section* in `contributions.md`. Leave out papers that add nothing the cited ones do not, papers outside the section's scope, and papers whose summaries cannot support what the plan would say about them. For each paper chosen, give its role and paragraph; for each paper in the set not chosen, one line saying why.

**Do not say.** Collect caveats from the summaries and the expand-stage judgments, and any "first" or "only" claims the evidence cannot support. Include a bounded novelty statement, of the form "Among the <N> papers read in full, none …", only as strong as the evidence supports.

**Known weaknesses.** Start this section with the taxonomy's *Possibly missing papers*: papers the field treats as part of a relevant category that are not in the synthesis set. This stage cannot add papers; the drafter should know that coverage may have a gap there.

Every statement about a paper must point to evidence in its summary, its expand-stage judgment, a verify result, the taxonomy, or the map.

### 11. Review, in place of human review
Spawn one `synthesis-reviewer` with `output: notes/synthesis-review.md`. If its verdict is `revise`, fix every *Must fix* item, and every *Should fix* item you can, then spawn it once more. If the second verdict is still `revise`, copy the remaining items into *Known weaknesses* in `notes/synthesis.md` so the drafter handles them carefully. Do not loop further. Record the final review status at the top of `notes/synthesis.md`.

### 12. Record the choice and finish
For each paper in *Papers to cite*: `python3 scripts/candidates.py set <id> status=keep decision_reason="cited: <role>"`. For each other paper in the set: `python3 scripts/candidates.py set <id> status=reject decision_reason="read in full, not cited: <reason>"`. Run `python3 scripts/candidates.py validate`.

Update `STATUS.md` as `CLAUDE.md` describes: stage 5 `done`, the date, and next action "Run `/lr-6-notes`". Report in a few lines:
- the size of the set and the number of papers chosen;
- the field's main categories;
- the organization chosen and why;
- the groups;
- every positioning correction;
- any possibly missing papers;
- the review result.
