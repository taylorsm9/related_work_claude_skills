# Data formats

Every machine-read file in the pipeline follows one of these formats. Agents must write exactly these fields. Unknown or missing values are `null`, never guessed.

## Identifiers and slugs

A paper's **`id`** is its most stable identifier, chosen in this order:

1. `doi:<doi>` (lowercase), for papers with a DOI
2. `arxiv:<arxiv id without version>`, e.g. `arxiv:2401.01234`
3. `s2:<Semantic Scholar paperId>`
4. `title:<normalized title>` only when nothing else exists (flag these)

The `id` is chosen when the record is created and **never changes afterwards**, because file names (slugs) and `found_via` entries refer to it. Identifiers found later are added to `ids`. Two records are the same paper if any of `ids.doi`, `ids.arxiv` or `ids.s2` match, or if normalized titles match and years differ by at most 1; `scripts/candidates.py add` merges them into the existing record. An arXiv preprint and its published version are one paper, with both identifiers in `ids`. arXiv's own DOIs (`10.48550/arXiv.*`) are stored as `ids.arxiv`, not as `ids.doi`, since they identify the preprint.

A **slug** is the `id` made safe for file names: replace `:` with `-`, and `/`, spaces and any other characters outside `[A-Za-z0-9._-]` with `_`. Example: `doi:10.1145/3580305.3599256` → `doi-10.1145_3580305.3599256`. `python3 scripts/candidates.py slug <id>` prints it.

A **normalized title** is lowercase, with punctuation removed and whitespace collapsed.

**Pages** always mean the PDF's page index as the Read tool reports it (1-based), not the number printed on the page.

## `research/candidates.jsonl`

One JSON object per line, one line per paper. Only the main session writes this file.

```json
{
  "id": "arxiv:2401.01234",
  "ids": {"doi": null, "arxiv": "2401.01234", "s2": "abc123...", "dblp": null},
  "title": "Exact title as returned by the source",
  "year": 2024,
  "venue": "NeurIPS",
  "authors": "Smith, Lee, Kim, et al.",
  "found_via": [
    {"stage": 1, "how": "arxiv-search", "detail": "query text", "date": "2026-10-17"},
    {"stage": 3, "how": "reference-of", "detail": "doi:10.1145/...", "cited_for": "how the citing paper uses it", "date": "2026-10-18"}
  ],
  "relations": {
    "C1": {"rel": "overlaps", "why": "one sentence"},
    "C2": {"rel": "unrelated", "why": "one sentence"}
  },
  "role": "closest-prior",
  "basis": "abstract",
  "priority": 1,
  "assessment_note": null,
  "relation_summary": "2-4 sentences on how this paper relates to the project, or null",
  "pdf": null,
  "expand_file": null,
  "status": "candidate",
  "decision_reason": null,
  "citekey": null,
  "updated": "2026-10-17"
}
```

| Field | Allowed values |
|---|---|
| `found_via[].how` | `arxiv-search`, `s2-search`, `dblp-search`, `s2-recommend`, `seed` (named in contributions), `reference-of`, `cited-by` (a paper that cites `detail`), `manual` (PDF added by the human) |
| `relations[Cn].rel` | `overlaps` (does part of what Cn claims), `differs` (same problem or method family, different in a way that matters for Cn), `unrelated`, `unclear` |
| `role` | `closest-prior`, `baseline`, `enabling` (a method, dataset or tool the project builds on), `background`, `off-topic` |
| `basis` | `metadata` (title only), `abstract`, `full-text` |
| `status` | `candidate`, `fetch-for-expand`, `expanded`, `keep`, `maybe`, `reject` |
| `priority` | 1 = must read in full, 2 = probably relevant, 3 = background at most, 4 = off-topic |


- A new record starts unjudged: `relations` is `{}` and `role`, `basis` and `priority` are `null`. Once judged, every claim in `project/contributions.md` must have an entry in `relations`.
- `priority` comes from the `candidate-assessor`; after the expand stage it is derived from the full-text judgment (1 if the paper overlaps a claim or is closest prior work or a baseline, 2 if it differs or is enabling, 3 otherwise, 4 if off-topic).
- `assessment_note` holds the assessor's note, or the expand status if the PDF was unreadable.
- `relation_summary` is filled in by the expand stage (full text); before that it is `null`.
- A full-text judgment is never overwritten by a later abstract-based assessment.

## `research/abstracts.jsonl`

A cache, one `{"id", "abstract"}` per line, written by `candidates.py add`. Abstracts are kept out of `candidates.jsonl` so it stays small enough to read.

## `research/assessments/<batch>.input.json` (written by `candidates.py make-batches`)

```json
{"batch": "s1-b03", "output": "research/assessments/s1-b03.json",
 "candidates": [{"id": "...", "title": "...", "year": 2024, "venue": "...", "authors": "...",
                 "abstract": "... or null", "found_via": []}]}
```

## `research/assessments/<batch>.json` (written by `candidate-assessor`)

```json
{
  "batch": "s1-b03",
  "assessments": [
    {
      "id": "arxiv:2401.01234",
      "relations": {"C1": {"rel": "overlaps", "why": "..."}, "C2": {"rel": "unrelated", "why": "..."}},
      "role": "closest-prior",
      "basis": "abstract",
      "priority": 1,
      "note": "optional: anything the screener should know, e.g. 'abstract vague on method'"
    }
  ]
}
```

`priority`: 1 = must read in full, 2 = probably relevant, 3 = background at most, 4 = off-topic.

## `research/expand/<slug>.json` (written by `paper-reader`)

```json
{
  "pdf": "expand/whatever-the-file-was-called.pdf",
  "status": "ok",
  "identified": {
    "title": "Title as printed on the first page",
    "authors": "First, Second, Third, et al.",
    "year": 2024,
    "venue": "as printed, or null",
    "ids_seen": {"doi": null, "arxiv": "2401.01234"},
    "matches_candidate": "arxiv:2401.01234",
    "confidence": "high"
  },
  "summary": "3-6 sentences: problem, method, evaluation, main result.",
  "relations": {
    "C1": {"rel": "overlaps", "why": "...", "evidence": [{"quote": "short exact quote", "page": 4}]},
    "C2": {"rel": "differs", "why": "...", "evidence": [{"quote": "...", "page": 6}]}
  },
  "role": "closest-prior",
  "relation_summary": "2-4 sentences on how this paper relates to the project.",
  "references_of_interest": [
    {
      "ref_text": "the bibliography entry as printed",
      "title": "title extracted from the entry",
      "year": 2022,
      "ids_seen": {"doi": null, "arxiv": null},
      "cited_for": "how this paper uses it, from the citing sentence",
      "page": 3,
      "relevant_to": ["C1"],
      "why": "one sentence"
    }
  ],
  "notes_for_later": "anything the note-writer or checker should look at, or null"
}
```

- `status`: `ok`, `unreadable` (scanned or broken PDF), `unidentified` (could not tell what paper it is).
- `ids_seen` holds only identifiers printed in the PDF. `matches_candidate` is the `id` of the candidate record the reader was given, or `null` for a manual PDF.
- `confidence`: `high` when title and authors are clearly printed, otherwise `low`.

## `checks/<citekey>.json` (written by `citation-checker`)

```json
{
  "citekey": "smith2024",
  "verdicts": [
    {
      "line": 12,
      "sentence": "the sentence as given in checks/sentences.json",
      "verdict": "supported",
      "evidence": [{"quote": "short exact quote", "page": 5}],
      "problem": null,
      "suggested_fix": null
    }
  ],
  "bib_issues": []
}
```

- `line` and `sentence` come from `checks/sentences.json` (written by `cites.py sentences`): `line` is where the sentence starts in `writing/related_work.tex`, and `sentence` is its text with comments removed and whitespace collapsed to single spaces. To find it in the file, go to `line` and match ignoring whitespace.
- `verdict`: `supported`, `partly` (true but overstated or imprecise), `unsupported` (the paper does not say this), `wrong-paper` (the claim belongs to a different work, often the original that this paper cites).
- `suggested_fix`: a minimal rewrite of the sentence, or of the citing clause, that the evidence supports; `null` when supported.
- `bib_issues`: strings, e.g. `"entry is the arXiv preprint; a published version exists"`, `"no DOI or arXiv ID"`.
