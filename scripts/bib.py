#!/usr/bin/env python3
"""Read library/refs.bib (a Better BibTeX export of the project's Zotero collection). Standard library only.

  bib.py list                     every entry: key, type, title, year, doi, arxiv, pdfs
  bib.py match --doi D | --arxiv A | --title T
  bib.py show KEY                 the raw entry text
  bib.py pdf KEY [--copy-to P]    the entry's PDF in Zotero's storage; optionally copy it to P
"""

import argparse
import filecmp
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ROOT, clean_doi, strip_arxiv_version, title_similarity  # noqa: E402

DEFAULT_BIB = os.path.join(ROOT, "library", "refs.bib")


def parse_bib(text):
    """Return a list of entries: {key, type, fields, raw}. Handles nested braces."""
    entries = []
    i = 0
    while True:
        m = re.compile(r"@(\w+)\s*[{(]").search(text, i)
        if not m:
            break
        etype = m.group(1).lower()
        start = m.start()
        j = m.end()
        opener = text[m.end() - 1]
        closer = "}" if opener == "{" else ")"
        depth = 1
        while j < len(text) and depth:
            if text[j] == opener:
                depth += 1
            elif text[j] == closer:
                depth -= 1
            j += 1
        body = text[m.end():j - 1]
        i = j
        if etype in ("comment", "string", "preamble"):
            continue
        key, _, rest = body.partition(",")
        entries.append({"key": key.strip(), "type": etype, "fields": parse_fields(rest),
                        "raw": text[start:j]})
    return entries


def parse_fields(s):
    fields = {}
    i = 0
    while i < len(s):
        m = re.compile(r"\s*([\w-]+)\s*=\s*").match(s, i)
        if not m:
            i += 1
            continue
        name = m.group(1).lower()
        j = m.end()
        if j < len(s) and s[j] == "{":
            depth, k = 1, j + 1
            while k < len(s) and depth:
                depth += {"{": 1, "}": -1}.get(s[k], 0)
                k += 1
            value = s[j + 1:k - 1]
        elif j < len(s) and s[j] == '"':
            k = s.find('"', j + 1)
            k = len(s) if k == -1 else k + 1
            value = s[j + 1:k - 1]
        else:
            k = j
            while k < len(s) and s[k] not in ",\n":
                k += 1
            value = s[j:k].strip()
        # File paths stay as written: collapsing whitespace would turn a no-break space in a
        # file name into a plain space and break the path.
        fields[name] = value.strip() if name == "file" else re.sub(r"\s+", " ", value).strip()
        i = k + 1
    return fields


def pdf_paths(fields):
    """PDF attachments listed in Better BibTeX's `file` field that exist on disk. The field holds
    paths separated by ';', either bare or JabRef-style 'description:path:mimetype'."""
    paths = []
    for part in re.split(r"(?<!\\);", fields.get("file") or ""):
        part = part.strip()
        m = re.match(r"^(.*?)(?<!\\):(.+)(?<!\\):([\w.+-]+/[\w.+-]+)$", part)
        if m:
            part = m.group(2)
        part = re.sub(r"(?<!\\)[{}]", "", part)
        part = re.sub(r"\\([\\:;{}_&%#$ ])", r"\1", part).strip()
        if part.lower().endswith(".pdf") and os.path.isfile(part):
            paths.append(part)
    return paths


def summary(e):
    f = e["fields"]
    arxiv = None
    if f.get("eprinttype", "").lower() == "arxiv" or f.get("archiveprefix", "").lower() == "arxiv":
        arxiv = strip_arxiv_version(f.get("eprint"))
    doi = clean_doi(f.get("doi"))
    if not arxiv and doi and doi.startswith("10.48550/arxiv."):
        arxiv = doi.split("arxiv.", 1)[1]
    if not arxiv:
        m = re.search(r"arxiv\.org/abs/([\w.\-/]+)", f.get("url", ""))
        arxiv = strip_arxiv_version(m.group(1)) if m else None
    title = re.sub(r"[{}]", "", f.get("title", ""))
    venue = re.sub(r"[{}]", "", f.get("journal") or f.get("journaltitle") or f.get("booktitle") or "") or None
    return {"key": e["key"], "type": e["type"], "title": title, "year": f.get("year") or f.get("date", "")[:4],
            "doi": doi, "arxiv": arxiv,
            "venue": venue,
            "is_preprint": (bool(arxiv) and not venue) or (doi or "").startswith("10.48550/"),
            "pdfs": pdf_paths(f)}


def copy_pdf(src, dest):
    """Copy src to dest. Never overwrites a different existing file; returns False if dest differs."""
    if os.path.exists(dest):
        return filecmp.cmp(src, dest, shallow=False)
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    shutil.copy2(src, dest)
    return True


def load(path):
    if not os.path.exists(path):
        sys.exit("%s not found. Export the Zotero collection there with Better BibTeX." % path)
    with open(path, encoding="utf-8") as f:
        return parse_bib(f.read())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bib", default=DEFAULT_BIB)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sp = sub.add_parser("match")
    sp.add_argument("--doi")
    sp.add_argument("--arxiv")
    sp.add_argument("--title")
    sp = sub.add_parser("show")
    sp.add_argument("key")
    sp = sub.add_parser("pdf")
    sp.add_argument("key")
    sp.add_argument("--copy-to", help="copy the PDF here (never overwrites a different file)")
    a = p.parse_args()

    entries = load(a.bib)
    if a.cmd == "list":
        for e in entries:
            print(json.dumps(summary(e), ensure_ascii=False))
    elif a.cmd == "show":
        for e in entries:
            if e["key"] == a.key:
                print(e["raw"])
                return
        sys.exit("no entry %r" % a.key)
    elif a.cmd == "pdf":
        entry = next((e for e in entries if e["key"] == a.key), None)
        if not entry:
            sys.exit("no entry %r" % a.key)
        paths = pdf_paths(entry["fields"])
        if not paths:
            sys.exit("%s: no PDF attachment found (no `file` field, or the file is missing)" % a.key)
        if a.copy_to:
            if not copy_pdf(paths[0], a.copy_to):
                sys.exit("%s already exists and is a different file; not overwritten" % a.copy_to)
            print("%s -> %s" % (paths[0], a.copy_to))
        else:
            print(paths[0])
    else:
        sums = [summary(e) for e in entries]
        hits = []
        if a.doi:
            hits = [s for s in sums if s["doi"] and s["doi"] == clean_doi(a.doi)]
        if not hits and a.arxiv:
            hits = [s for s in sums if s["arxiv"] and s["arxiv"] == strip_arxiv_version(a.arxiv)]
        if not hits and a.title:
            scored = sorted(((title_similarity(a.title, s["title"]), s) for s in sums),
                            key=lambda x: -x[0])
            hits = [dict(s, title_similarity=round(sc, 3)) for sc, s in scored if sc >= 0.9]
        if not hits:
            print("no match")
            sys.exit(1)
        for h in hits:
            print(json.dumps(h, ensure_ascii=False))


if __name__ == "__main__":
    main()
