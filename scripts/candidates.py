#!/usr/bin/env python3
"""Maintain research/candidates.jsonl (one record per paper). See templates/schemas.md.

Only the main session runs the commands that write (add, add-manual, merge-*, set).
Standard library only.
"""

import argparse
import datetime as dt
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (ABSTRACTS, CANDIDATES, ROOT, claim_ids, clean_doi, empty_ids,  # noqa: E402
                     make_id, norm_title, read_json, read_jsonl, slug, strip_arxiv_version,
                     title_similarity, write_json, write_jsonl)

HOWS = {"arxiv-search", "s2-search", "dblp-search", "s2-recommend", "seed", "reference-of",
        "cited-by", "manual"}
RELS = {"overlaps", "differs", "unrelated", "unclear"}
ROLES = {"closest-prior", "baseline", "enabling", "background", "off-topic"}
BASES = {"metadata", "abstract", "full-text"}
STATUSES = {"candidate", "fetch-for-expand", "expanded", "keep", "maybe", "reject"}
SETTABLE = {"status", "decision_reason", "citekey", "pdf", "priority", "role"}
REL_ABBR = {"overlaps": "o", "differs": "d", "unrelated": "-", "unclear": "?"}
ASSESS_DIR = os.path.join(ROOT, "research", "assessments")


def today():
    return dt.date.today().isoformat()


def load():
    return read_jsonl(CANDIDATES)


def save(rows):
    write_jsonl(CANDIDATES, rows)


def load_abstracts():
    return {r["id"]: r.get("abstract") for r in read_jsonl(ABSTRACTS)}


def save_abstracts(cache):
    write_jsonl(ABSTRACTS, [{"id": k, "abstract": v} for k, v in sorted(cache.items()) if v])


def same_paper(a, b):
    for k in ("doi", "arxiv", "s2"):
        if a["ids"].get(k) and a["ids"].get(k) == b["ids"].get(k):
            return True
    ta, tb = norm_title(a.get("title")), norm_title(b.get("title"))
    if ta and ta == tb:
        ya, yb = a.get("year"), b.get("year")
        return ya is None or yb is None or abs(ya - yb) <= 1
    return False


def find_all(rows, rec):
    return [r for r in rows if r["id"] == rec.get("id") or same_paper(r, rec)]


def find_existing(rows, rec):
    hits = find_all(rows, rec)
    return hits[0] if hits else None


STATUS_RANK = {"reject": 0, "candidate": 1, "fetch-for-expand": 2, "expanded": 3, "maybe": 4, "keep": 5}


def fold(keep, drop, cache):
    """Merge record `drop` into `keep` (same paper). `keep` keeps its id."""
    for k, v in drop["ids"].items():
        if v and not keep["ids"].get(k):
            keep["ids"][k] = v
    for k in ("title", "year", "venue", "authors"):
        if not keep.get(k) and drop.get(k):
            keep[k] = drop[k]
    for f in drop["found_via"]:
        if all((g["stage"], g["how"], g["detail"]) != (f["stage"], f["how"], f["detail"]) for g in keep["found_via"]):
            keep["found_via"].append(f)
    judged_better = drop.get("relations") and (
        not keep.get("relations") or (drop.get("basis") == "full-text" and keep.get("basis") != "full-text"))
    if judged_better:
        for k in ("relations", "role", "basis", "priority", "assessment_note", "relation_summary", "expand_file"):
            keep[k] = drop.get(k)
    for k in ("pdf", "expand_file", "citekey", "decision_reason", "relation_summary"):
        if not keep.get(k) and drop.get(k):
            keep[k] = drop[k]
    if STATUS_RANK.get(drop["status"], 0) > STATUS_RANK.get(keep["status"], 0):
        keep["status"] = drop["status"]
    if cache.get(drop["id"]) and not cache.get(keep["id"]):
        cache[keep["id"]] = cache[drop["id"]]
    cache.pop(drop["id"], None)
    keep["updated"] = today()


def fold_duplicates(rows, rec, cache):
    """If rec now matches other records (e.g. preprint and published version), fold them into rec."""
    merged = []
    changed = True
    while changed:
        changed = False
        for other in list(rows):
            if other is not rec and same_paper(rec, other):
                first, second = (rec, other) if rows.index(rec) < rows.index(other) else (other, rec)
                fold(first, second, cache)
                rows.remove(second)
                merged.append(second["id"])
                rec = first
                changed = True
                break
    return rec, merged


def by_id(rows, record_id):
    for r in rows:
        if r["id"] == record_id:
            return r
    sys.exit("no candidate with id %r (try: candidates.py find --id ...)" % record_id)


def new_record(src):
    ids = empty_ids()
    ids.update({k: v for k, v in (src.get("ids") or {}).items() if k in ids and v})
    return {
        "id": src.get("id") or make_id(ids, src.get("title")),
        "ids": ids,
        "title": src.get("title"),
        "year": src.get("year"),
        "venue": src.get("venue"),
        "authors": src.get("authors"),
        "found_via": [],
        "relations": {},
        "role": None,
        "basis": None,
        "priority": None,
        "assessment_note": None,
        "relation_summary": None,
        "pdf": None,
        "expand_file": None,
        "status": "candidate",
        "decision_reason": None,
        "citekey": None,
        "updated": today(),
    }


def merge_into(existing, src):
    for k, v in (src.get("ids") or {}).items():
        if v and not existing["ids"].get(k):
            existing["ids"][k] = v
    for k in ("title", "year", "venue", "authors"):
        if not existing.get(k) and src.get(k):
            existing[k] = src[k]
    existing["updated"] = today()


def add_via(rec, stage, how, detail, cited_for=None):
    entry = {"stage": stage, "how": how, "detail": detail, "date": today()}
    if cited_for:
        entry["cited_for"] = cited_for
    for f in rec["found_via"]:
        if (f["stage"], f["how"], f["detail"]) == (stage, how, detail):
            return
    rec["found_via"].append(entry)


def incoming(path):
    data = read_json(path) if path != "-" else json.load(sys.stdin)
    if isinstance(data, dict):
        data = data.get("records", [])
    return data


# ---------------------------------------------------------------- commands

def cmd_claims(a):
    ids = claim_ids()
    if not ids:
        sys.exit("no claims found: project/contributions.md needs headings like '### C1: ...'")
    print(" ".join(ids))


def cmd_add(a):
    if a.how not in HOWS:
        sys.exit("--how must be one of: " + ", ".join(sorted(HOWS)))
    rows, cache = load(), load_abstracts()
    added = merged = abstracts = 0
    folded, report = [], []
    for src in incoming(a.file):
        if not src.get("title"):
            continue
        rec = find_existing(rows, src)
        if a.abstracts_only:
            if rec:
                merge_into(rec, src)
                rec, gone = fold_duplicates(rows, rec, cache)
                folded += gone
                if src.get("abstract") and not cache.get(rec["id"]):
                    cache[rec["id"]] = src["abstract"]
                    abstracts += 1
            continue
        if rec:
            merge_into(rec, src)
            merged += 1
            kind = "merged"
        else:
            rec = new_record(src)
            rows.append(rec)
            added += 1
            kind = "new"
        rec, gone = fold_duplicates(rows, rec, cache)
        folded += gone
        add_via(rec, a.stage, a.how, a.detail, (src.get("extra") or {}).get("cited_for"))
        if src.get("abstract") and not cache.get(rec["id"]):
            cache[rec["id"]] = src["abstract"]
            abstracts += 1
        report.append("%s %s" % (kind, rec["id"]))
    save(rows)
    save_abstracts(cache)
    if a.print_ids:
        for line in report:
            print(line)
    if a.abstracts_only:
        print("abstracts added: %d" % abstracts)
    else:
        print("hits: %d, new candidates: %d, already known: %d, abstracts cached: %d"
              % (added + merged, added, merged, abstracts))
    for gone in folded:
        print("folded duplicate %s into an earlier record (same paper)" % gone)


def cmd_merge(a):
    rows, cache = load(), load_abstracts()
    keep, drop = by_id(rows, a.keep), by_id(rows, a.drop)
    fold(keep, drop, cache)
    rows.remove(drop)
    save(rows)
    save_abstracts(cache)
    print("merged %s into %s" % (a.drop, a.keep))


def cmd_add_manual(a):
    rows = load()
    year = int(a.year) if a.year and a.year.isdigit() else None
    src = {"title": a.title, "year": year, "authors": a.authors, "ids": {}}
    rec = find_existing(rows, src)
    if not rec:
        rec = new_record(src)
        rows.append(rec)
    rec["pdf"] = a.pdf
    add_via(rec, 3, "manual", a.pdf)
    save(rows)
    print(rec["id"])


def cmd_missing_abstracts(a):
    cache = load_abstracts()
    for r in load():
        if not r["relations"] and not cache.get(r["id"]) and not r["id"].startswith("title:"):
            print(r["id"])


def batched_ids():
    """Ids already in an input batch whose output has not been merged yet."""
    ids = set()
    for path in glob.glob(os.path.join(ASSESS_DIR, "*.input.json")):
        out = path.replace(".input.json", ".json")
        if not os.path.exists(out):
            ids.update(c["id"] for c in read_json(path).get("candidates", []))
    return ids


def cmd_make_batches(a):
    rows, cache = load(), load_abstracts()
    skip = batched_ids()
    pending = [r for r in rows if not r["relations"] and r["status"] != "reject" and r["id"] not in skip]
    if not pending:
        print("nothing to assess")
        return
    existing = glob.glob(os.path.join(ASSESS_DIR, a.prefix + "-b*.input.json"))
    start = len(existing) + 1
    for i in range(0, len(pending), a.size):
        n = start + i // a.size
        batch = "%s-b%02d" % (a.prefix, n)
        items = [{"id": r["id"], "title": r["title"], "year": r["year"], "venue": r["venue"],
                  "authors": r["authors"], "abstract": cache.get(r["id"]), "found_via": r["found_via"]}
                 for r in pending[i:i + a.size]]
        path = os.path.join(ASSESS_DIR, batch + ".input.json")
        write_json(path, {"batch": batch, "output": "research/assessments/%s.json" % batch,
                          "candidates": items})
        print("%s  (%d candidates)  -> output research/assessments/%s.json"
              % (os.path.relpath(path, ROOT), len(items), batch))


def cmd_merge_assessment(a):
    rows = load()
    data = read_json(a.file)
    done = skipped = 0
    for item in data.get("assessments", []):
        rec = by_id(rows, item["id"])
        if rec.get("basis") == "full-text":
            skipped += 1
            continue
        rec["relations"] = {k: {"rel": v["rel"], "why": v.get("why")} for k, v in item["relations"].items()}
        rec["role"] = item.get("role")
        rec["basis"] = item.get("basis", "abstract")
        rec["priority"] = item.get("priority")
        rec["assessment_note"] = item.get("note")
        rec["updated"] = today()
        done += 1
    save(rows)
    print("merged: %d, kept existing full-text judgment: %d" % (done, skipped))


def derived_priority(relations, role):
    rels = {v["rel"] for v in relations.values()}
    if role == "off-topic":
        return 4
    if "overlaps" in rels or role in ("closest-prior", "baseline"):
        return 1
    if "differs" in rels or role == "enabling":
        return 2
    return 3


def cmd_merge_expand(a):
    rows = load()
    rec = by_id(rows, a.id)
    data = read_json(a.file)
    if data.get("status") != "ok":
        rec["assessment_note"] = "expand: %s" % data.get("status")
    if data.get("relations"):
        rec["relations"] = {k: {"rel": v["rel"], "why": v.get("why")} for k, v in data["relations"].items()}
        rec["role"] = data.get("role")
        rec["basis"] = "full-text"
        rec["priority"] = derived_priority(rec["relations"], rec["role"])
    rec["relation_summary"] = data.get("relation_summary")
    rec["expand_file"] = os.path.relpath(os.path.abspath(a.file), ROOT)
    rec["pdf"] = rec.get("pdf") or data.get("pdf")
    seen = (data.get("identified") or {}).get("ids_seen") or {}
    if seen.get("doi") and not rec["ids"]["doi"]:
        rec["ids"]["doi"] = clean_doi(seen["doi"])
    if seen.get("arxiv") and not rec["ids"]["arxiv"]:
        rec["ids"]["arxiv"] = strip_arxiv_version(seen["arxiv"])
    if data.get("status") == "ok" and rec["status"] in ("candidate", "fetch-for-expand"):
        rec["status"] = "expanded"
    rec["updated"] = today()
    save(rows)
    print("%s: basis=%s role=%s priority=%s" % (rec["id"], rec["basis"], rec["role"], rec["priority"]))


def cmd_set(a):
    rows = load()
    rec = by_id(rows, a.id)
    for pair in a.pairs:
        if "=" not in pair:
            sys.exit("expected field=value, got %r" % pair)
        k, v = pair.split("=", 1)
        if k not in SETTABLE:
            sys.exit("can only set: " + ", ".join(sorted(SETTABLE)))
        if v in ("", "null", "None"):
            v = None
        elif k == "priority":
            v = int(v)
        rec[k] = v
    rec["updated"] = today()
    save(rows)
    print("%s updated" % rec["id"])


def cmd_validate(a):
    rows = load()
    claims = claim_ids()
    errors, warnings = [], []
    seen_ids, seen_ext = {}, {}
    for n, r in enumerate(rows, 1):
        where = "line %d (%s)" % (n, r.get("id"))
        for key in ("id", "ids", "title", "found_via", "relations", "status"):
            if key not in r:
                errors.append("%s: missing field %r" % (where, key))
        if r.get("id") in seen_ids:
            errors.append("%s: duplicate id (also line %d)" % (where, seen_ids[r["id"]]))
        seen_ids[r.get("id")] = n
        for k in ("doi", "arxiv", "s2"):
            v = (r.get("ids") or {}).get(k)
            if v:
                if (k, v) in seen_ext:
                    errors.append("%s: same %s as line %d; run 'candidates.py merge <id to keep> <id to drop>'"
                                  % (where, k, seen_ext[(k, v)]))
                seen_ext[(k, v)] = n
        if r.get("status") not in STATUSES:
            errors.append("%s: bad status %r" % (where, r.get("status")))
        for f in r.get("found_via", []):
            if f.get("how") not in HOWS:
                errors.append("%s: bad found_via.how %r" % (where, f.get("how")))
        rels = r.get("relations") or {}
        for c, v in rels.items():
            if v.get("rel") not in RELS:
                errors.append("%s: %s has bad rel %r" % (where, c, v.get("rel")))
        if rels:
            if r.get("basis") not in BASES:
                errors.append("%s: judged but basis is %r" % (where, r.get("basis")))
            if r.get("role") not in ROLES:
                errors.append("%s: judged but role is %r" % (where, r.get("role")))
            missing = [c for c in claims if c not in rels]
            if missing:
                warnings.append("%s: no judgment for %s" % (where, ", ".join(missing)))
        if r.get("status") == "keep" and not rels:
            errors.append("%s: kept but never judged" % where)
        if r.get("id", "").startswith("title:"):
            warnings.append("%s: no DOI, arXiv or S2 id" % where)
    for w in warnings:
        print("warning: " + w)
    for e in errors:
        print("ERROR: " + e)
    print("%d records, %d errors, %d warnings" % (len(rows), len(errors), len(warnings)))
    sys.exit(1 if errors else 0)


def rel_cells(r, claims):
    return [REL_ABBR.get((r["relations"].get(c) or {}).get("rel"), "") for c in claims]


def sort_key(r):
    order = ["keep", "maybe", "expanded", "fetch-for-expand", "candidate", "reject"]
    return (order.index(r["status"]) if r["status"] in order else 9, r.get("priority") or 9,
            -(r.get("year") or 0))


def cmd_render(a):
    rows, claims = sorted(load(), key=sort_key), claim_ids()
    head = ["Paper", "Year", "Role"] + claims + ["Basis", "Pri", "Found via", "Status"]
    lines = ["# Candidates", "",
             "Generated from `research/candidates.jsonl` on %s. Do not edit; it is overwritten." % today(),
             "Claim cells: o = overlaps, d = differs, - = unrelated, ? = unclear.", "",
             "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        hows = sorted({f["how"] for f in r["found_via"]})
        cells = ["%s (`%s`)" % ((r["title"] or "").replace("|", "/"), r["id"]), str(r.get("year") or ""),
                 r.get("role") or ""] + rel_cells(r, claims) + [
                 r.get("basis") or "", str(r.get("priority") or ""), ", ".join(hows), r["status"]]
        lines.append("| " + " | ".join(cells) + " |")
    out = a.out or os.path.join(ROOT, "research", "candidates.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote %s (%d rows)" % (os.path.relpath(out, ROOT), len(rows)))


def cmd_list(a):
    claims = claim_ids()
    for r in sorted(load(), key=sort_key):
        if a.status and r["status"] != a.status:
            continue
        if a.priority_max and (r.get("priority") or 9) > a.priority_max:
            continue
        if a.role and r.get("role") != a.role:
            continue
        if a.basis and r.get("basis") != a.basis:
            continue
        if a.missing_pdf and r.get("pdf"):
            continue
        if a.json:
            print(json.dumps(r, ensure_ascii=False))
            continue
        rels = " ".join("%s:%s" % (c, x or "") for c, x in zip(claims, rel_cells(r, claims)))
        print(" | ".join([r["id"], str(r.get("year") or ""), (r["title"] or "")[:100], r.get("role") or "",
                          "p%s" % (r.get("priority") or "?"), r.get("basis") or "", rels, r["status"],
                          r.get("citekey") or ""]))


def cmd_stats(a):
    rows, claims = load(), claim_ids()
    print("candidates screened: %d" % len(rows))
    for field in ("status", "basis", "priority", "role"):
        counts = {}
        for r in rows:
            counts[str(r.get(field))] = counts.get(str(r.get(field)), 0) + 1
        print("%s: %s" % (field, ", ".join("%s=%d" % kv for kv in sorted(counts.items()))))
    for c in claims:
        ov = sum(1 for r in rows if (r["relations"].get(c) or {}).get("rel") == "overlaps")
        ovf = sum(1 for r in rows if (r["relations"].get(c) or {}).get("rel") == "overlaps"
                  and r.get("basis") == "full-text")
        print("%s: %d overlapping (%d from full text)" % (c, ov, ovf))
    print("unjudged: %d" % sum(1 for r in rows if not r["relations"]))


def cmd_find(a):
    rows = load()
    hits = []
    if a.id:
        kind, _, value = a.id.partition(":")
        for r in rows:
            if r["id"] == a.id or r["ids"].get(kind) == value:
                hits.append(r)
    if a.title:
        hits += [r for r in rows if title_similarity(a.title, r["title"]) >= 0.85 and r not in hits]
    for r in hits:
        print(json.dumps(r, ensure_ascii=False))
    if not hits:
        print("no match")


def cmd_slug(a):
    print(slug(a.id))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("claims", help="print the claim ids from project/contributions.md").set_defaults(fn=cmd_claims)

    sp = sub.add_parser("add", help="add lit.py results as candidates (dedupes, records found_via)")
    sp.add_argument("file", help="lit.py JSON output, or - for stdin")
    sp.add_argument("--stage", type=int, required=True)
    sp.add_argument("--how", required=True)
    sp.add_argument("--detail", required=True, help="the query, or the id of the citing/cited paper")
    sp.add_argument("--abstracts-only", action="store_true", help="only fill cached abstracts")
    sp.add_argument("--print-ids", action="store_true", help="print 'new <id>' or 'merged <id>' per record")
    sp.set_defaults(fn=cmd_add)

    sp = sub.add_parser("merge", help="merge two records of the same paper (keeps the first id)")
    sp.add_argument("keep")
    sp.add_argument("drop")
    sp.set_defaults(fn=cmd_merge)

    sp = sub.add_parser("add-manual", help="add a manual PDF that no index could identify")
    sp.add_argument("--title", required=True)
    sp.add_argument("--year", help="omit if unknown")
    sp.add_argument("--authors")
    sp.add_argument("--pdf", required=True)
    sp.set_defaults(fn=cmd_add_manual)

    sub.add_parser("missing-abstracts", help="ids of unjudged candidates with no cached abstract"
                   ).set_defaults(fn=cmd_missing_abstracts)

    sp = sub.add_parser("make-batches", help="write assessment input batches for unjudged candidates")
    sp.add_argument("--prefix", required=True, help="e.g. s1 or s3r1")
    sp.add_argument("--size", type=int, default=10)
    sp.set_defaults(fn=cmd_make_batches)

    sp = sub.add_parser("merge-assessment", help="merge a candidate-assessor output file")
    sp.add_argument("file")
    sp.set_defaults(fn=cmd_merge_assessment)

    sp = sub.add_parser("merge-expand", help="merge a paper-reader output file")
    sp.add_argument("file")
    sp.add_argument("--id", required=True)
    sp.set_defaults(fn=cmd_merge_expand)

    sp = sub.add_parser("set", help="set fields: status, decision_reason, citekey, pdf, priority, role")
    sp.add_argument("id")
    sp.add_argument("pairs", nargs="+", metavar="field=value")
    sp.set_defaults(fn=cmd_set)

    sub.add_parser("validate", help="check the file against templates/schemas.md").set_defaults(fn=cmd_validate)

    sp = sub.add_parser("render", help="write research/candidates.md for humans")
    sp.add_argument("--out")
    sp.set_defaults(fn=cmd_render)

    sp = sub.add_parser("list", help="one compact line per candidate")
    sp.add_argument("--status")
    sp.add_argument("--priority-max", type=int)
    sp.add_argument("--role")
    sp.add_argument("--basis")
    sp.add_argument("--missing-pdf", action="store_true", help="only records with no pdf")
    sp.add_argument("--json", action="store_true", help="print full records (ids, pdf, links) as JSON lines")
    sp.set_defaults(fn=cmd_list)

    sub.add_parser("stats", help="counts by status, basis, priority, role, and per claim").set_defaults(fn=cmd_stats)

    sp = sub.add_parser("find", help="find records by id or similar title")
    sp.add_argument("--id")
    sp.add_argument("--title")
    sp.set_defaults(fn=cmd_find)

    sp = sub.add_parser("slug", help="file-name-safe form of an id")
    sp.add_argument("id")
    sp.set_defaults(fn=cmd_slug)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
