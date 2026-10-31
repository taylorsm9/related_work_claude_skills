# Papers to fetch for expand

Written by: stage <n> on <date>

<!-- A stage that adds a round to an existing list appends "## Round <n>" with the same three
     sections one heading level down (### What to do, ### On arXiv only, ### Published version exists). -->

## What to do

<!-- The generating stage replaces this section with the instructions for this list. The standard text:

1. Once per project: in Zotero, create a collection for this paper, and set up a Better BibTeX automatic
   export of it (format *Better BibTeX*, *Keep updated* ticked) to `library/refs.bib` in this repository.
   The export must include attachment paths (the `file` field); the next stage reports it if they are missing.
2. For each paper below, open its link and save it into that collection with the Zotero connector, with its PDF.
   Under *Published version exists*, save the published version where you can get its PDF; otherwise save the
   arXiv version.
3. You can also save any other paper you think is relevant into the collection, or drop a PDF into `expand/`;
   the expand stage identifies it.
4. Run `/lr-3-expand`.
-->

## On arXiv only

<!-- One block per paper, most important first. Links come from tool results only.
     Link the arXiv abstract page, never the PDF: Zotero's connector reads the metadata from the
     abstract page and saves the PDF with it. -->

### 1. <Title> (<year>)
- **Why:** <one line: which claim, what role>
- **arXiv:** https://arxiv.org/abs/<id>
- **id:** `<id>`
- [ ] in Zotero with PDF

## Published version exists

<!-- Papers with a version outside arXiv (proceedings or journal): `extra.published` is true in the output of
     `python3 scripts/lit.py published-links`. Give its `best_link` (page links come first) and the other
     `links`; if it found none, write "no link found" and the venue, so the human can look it up. -->

### 1. <Title> (<year>, <published venue or journal>)
- **Why:** <one line: which claim, what role>
- **Published version:** <best_link> — or: no link found; venue: <published venue or journal>
- **Other links:** <the remaining links, each with its kind>
- **arXiv:** https://arxiv.org/abs/<id> <!-- omit if the paper has no arXiv ID -->
- **id:** `<id>`
- [ ] in Zotero with PDF
