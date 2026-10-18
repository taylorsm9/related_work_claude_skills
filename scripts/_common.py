"""Shared helpers for the pipeline scripts. Standard library only."""

import json
import os
import re
import sys
import unicodedata
from difflib import SequenceMatcher

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CANDIDATES = os.path.join(ROOT, "research", "candidates.jsonl")
ABSTRACTS = os.path.join(ROOT, "research", "abstracts.jsonl")
CONTRIBUTIONS = os.path.join(ROOT, "project", "contributions.md")


def norm_title(title):
    """Lowercase, strip accents and punctuation, collapse whitespace."""
    if not title:
        return ""
    t = unicodedata.normalize("NFKD", title)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"[{}\\$]", "", t)  # LaTeX braces and math markers
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def title_similarity(a, b):
    return SequenceMatcher(None, norm_title(a), norm_title(b)).ratio()


def strip_arxiv_version(arxiv_id):
    if not arxiv_id:
        return None
    a = arxiv_id.strip()
    a = re.sub(r"^(arxiv:)", "", a, flags=re.I)
    a = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", a)
    a = re.sub(r"\.pdf$", "", a)
    return re.sub(r"v\d+$", "", a)


def clean_doi(doi):
    if not doi:
        return None
    d = doi.strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.I)
    d = re.sub(r"^doi:", "", d, flags=re.I)
    return d.lower() or None


def make_id(ids, title=None):
    """Choose the record id by the order in templates/schemas.md."""
    if ids.get("doi"):
        return "doi:" + ids["doi"]
    if ids.get("arxiv"):
        return "arxiv:" + ids["arxiv"]
    if ids.get("s2"):
        return "s2:" + ids["s2"]
    return "title:" + norm_title(title)


def slug(record_id):
    s = record_id.replace(":", "-", 1)
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)


def empty_ids():
    return {"doi": None, "arxiv": None, "s2": None, "dblp": None}


def parse_id(record_id):
    """Split 'doi:10.1/x' into ('doi', '10.1/x')."""
    if ":" not in record_id:
        raise ValueError("id must look like doi:..., arxiv:..., s2:... or title:...: %r" % record_id)
    kind, value = record_id.split(":", 1)
    kind = kind.lower()
    if kind not in ("doi", "arxiv", "s2", "title"):
        raise ValueError("unknown id kind %r in %r" % (kind, record_id))
    return kind, value


def read_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.exit("%s line %d is not valid JSON: %s" % (path, n, e))
    return rows


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def emit(data, out=None):
    """Write JSON to a file (and print a short summary) or to stdout."""
    if out:
        write_json(out, data)
        n = len(data) if isinstance(data, list) else len(data.get("records", []))
        print("wrote %s (%d records)" % (out, n))
    else:
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")


def claim_ids(path=CONTRIBUTIONS):
    """Claim ids (C1, C2, ...) from '### C1: ...' headings in contributions.md."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return re.findall(r"^#{2,4}\s*(C\d+)\b", text, flags=re.M)
