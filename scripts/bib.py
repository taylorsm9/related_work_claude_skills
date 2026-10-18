#!/usr/bin/env python3
"""Read library/refs.bib (a Better BibTeX export). Standard library only.

  bib.py list                     every entry: key, type, title, year, doi, arxiv
  bib.py match --doi D | --arxiv A | --title T
  bib.py show KEY                 the raw entry text
"""

import argparse
import json
import os
import re
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
        fields[name] = re.sub(r"\s+", " ", value).strip()
        i = k + 1
    return fields


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
            "is_preprint": (bool(arxiv) and not venue) or (doi or "").startswith("10.48550/")}


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
