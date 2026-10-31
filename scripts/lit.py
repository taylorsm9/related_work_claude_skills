#!/usr/bin/env python3
"""Literature lookups for the pipeline: arXiv, Semantic Scholar (S2) and DBLP.

Every command prints a JSON list of normalized records (or writes it with --out):

  {"id", "ids": {"doi","arxiv","s2","dblp"}, "title", "year", "venue", "authors",
   "abstract", "url", "citation_count", "extra": {...}}

IDs on the command line use the pipeline format: doi:<doi>, arxiv:<id>, s2:<paperId>.
Set S2_API_KEY in the environment to use a Semantic Scholar key.
Standard library only.
"""

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (clean_doi, emit, empty_ids, make_id, norm_title, read_json,  # noqa: E402
                     strip_arxiv_version, title_similarity)

S2_GRAPH = "https://api.semanticscholar.org/graph/v1"
S2_RECS = "https://api.semanticscholar.org/recommendations/v1"
ARXIV_API = "https://export.arxiv.org/api/query"
DBLP_API = "https://dblp.org/search/publ/api"
S2_FIELDS = "paperId,externalIds,title,year,venue,authors,citationCount,url"
USER_AGENT = "related_work_claude_skills/0.1 (%s)" % os.environ.get("LIT_MAILTO", "no contact set")

_last_call = {}
_MIN_GAP = {"s2": 1.1, "arxiv": 3.1, "dblp": 1.0}


def _pace(service):
    gap = _MIN_GAP[service]
    since = time.time() - _last_call.get(service, 0)
    if since < gap:
        time.sleep(gap - since)
    _last_call[service] = time.time()


def http(service, url, params=None, body=None, raw=False, allow_404=False):
    if params:
        url = url + "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    headers = {"User-Agent": USER_AGENT}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if service == "s2" and os.environ.get("S2_API_KEY"):
        headers["x-api-key"] = os.environ["S2_API_KEY"]
    delay = 2.0
    for attempt in range(5):
        _pace(service)
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = resp.read()
                return payload.decode("utf-8") if raw else json.loads(payload)
        except urllib.error.HTTPError as e:
            if e.code == 404 and allow_404:
                return None
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(delay)
                delay *= 2
                continue
            detail = e.read().decode("utf-8", "replace")[:300]
            sys.exit("HTTP %d from %s: %s" % (e.code, url.split("?")[0], detail))
        except urllib.error.URLError as e:
            if attempt < 4:
                time.sleep(delay)
                delay *= 2
                continue
            sys.exit("network error for %s: %s" % (url.split("?")[0], e.reason))
    sys.exit("giving up on %s" % url.split("?")[0])


def record(ids, title, year=None, venue=None, authors=None, abstract=None, url=None,
           citation_count=None, extra=None):
    full = empty_ids()
    full.update({k: v for k, v in ids.items() if v})
    # arXiv's own DataCite DOIs (10.48550/arXiv.*) identify the preprint, not a published version.
    if full["doi"] and full["doi"].startswith("10.48550/arxiv."):
        full["arxiv"] = full["arxiv"] or full["doi"].split("arxiv.", 1)[1]
        full["doi"] = None
    return {
        "id": make_id(full, title),
        "ids": full,
        "title": (title or "").strip(),
        "year": year,
        "venue": venue or None,
        "authors": authors,
        "abstract": abstract,
        "url": url,
        "citation_count": citation_count,
        "extra": extra or {},
    }


def author_string(names):
    names = [n for n in names if n]
    if not names:
        return None
    if len(names) > 3:
        return ", ".join(names[:3]) + ", et al."
    return ", ".join(names)


# ---------------------------------------------------------------- Semantic Scholar

def s2_ref(record_id):
    """Pipeline id -> S2 paper reference."""
    kind, value = record_id.split(":", 1) if ":" in record_id else ("s2", record_id)
    kind = kind.lower()
    if kind == "doi":
        return "DOI:" + value
    if kind == "arxiv":
        return "ARXIV:" + strip_arxiv_version(value)
    if kind == "s2":
        return value
    sys.exit("cannot look up %r in Semantic Scholar; use doi:, arxiv: or s2:" % record_id)


def s2_record(p, extra=None):
    if not p or not p.get("paperId"):
        return None
    ext = p.get("externalIds") or {}
    ids = {
        "doi": clean_doi(ext.get("DOI")),
        "arxiv": strip_arxiv_version(ext.get("ArXiv")),
        "s2": p.get("paperId"),
        "dblp": ext.get("DBLP"),
    }
    authors = author_string([a.get("name") for a in (p.get("authors") or [])])
    return record(ids, p.get("title"), p.get("year"), p.get("venue"), authors,
                  p.get("abstract"), p.get("url"), p.get("citationCount"), extra)


def fields(abstract):
    return S2_FIELDS + (",abstract" if abstract else "")


def s2_search(a):
    params = {"query": a.query, "limit": min(a.limit, 100), "fields": fields(True)}
    if a.year:
        params["year"] = a.year
    if a.fields_of_study:
        params["fieldsOfStudy"] = a.fields_of_study
    res = http("s2", S2_GRAPH + "/paper/search", params)
    return [r for r in (s2_record(p) for p in res.get("data") or []) if r]


def s2_match_title(title, abstract=True):
    res = http("s2", S2_GRAPH + "/paper/search/match",
               {"query": title, "fields": fields(abstract)}, allow_404=True)
    if not res or not res.get("data"):
        return None
    p = res["data"][0]
    rec = s2_record(p, {"match_score": p.get("matchScore"),
                        "title_similarity": round(title_similarity(title, p.get("title")), 3)})
    return rec


def s2_match(a):
    rec = s2_match_title(a.title)
    if not rec:
        return []
    if rec["extra"]["title_similarity"] < 0.9:
        rec["extra"]["warning"] = "returned title differs from the query; check before using"
    return [rec]


def s2_paper(a):
    p = http("s2", S2_GRAPH + "/paper/" + urllib.parse.quote(s2_ref(a.id), safe=":/"),
             {"fields": fields(a.abstract)}, allow_404=True)
    rec = s2_record(p)
    return [rec] if rec else []


def s2_batch_ids(id_list, abstract):
    out = []
    for i in range(0, len(id_list), 500):
        chunk = id_list[i:i + 500]
        res = http("s2", S2_GRAPH + "/paper/batch", {"fields": fields(abstract)},
                   body={"ids": [s2_ref(x) for x in chunk]})
        for asked, p in zip(chunk, res):
            rec = s2_record(p)
            if rec:
                rec["extra"]["requested_id"] = asked
                out.append(rec)
    return out


def id_args(a):
    ids = list(a.ids or [])
    if a.ids_file:
        with open(a.ids_file, encoding="utf-8") as f:
            ids += [line.strip() for line in f if line.strip()]
    return ids


def s2_batch(a):
    return s2_batch_ids(id_args(a), a.abstract)


PUB_FIELDS = "paperId,externalIds,title,year,venue,authors,url,publicationVenue,journal,openAccessPdf"


def _arxiv_only(name):
    name = (name or "").strip().lower()
    return not name or "arxiv" in name or name == "corr"


def published_links(a):
    """Whether each paper has a version outside arXiv, and links to it (page links first)."""
    ids = id_args(a)
    out = []
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        res = http("s2", S2_GRAPH + "/paper/batch", {"fields": PUB_FIELDS},
                   body={"ids": [s2_ref(x) for x in chunk]})
        for asked, p in zip(chunk, res):
            rec = s2_record(p)
            if not rec:
                out.append({"id": asked, "ids": empty_ids(), "title": None, "year": None, "venue": None,
                            "authors": None, "abstract": None, "url": None, "citation_count": None,
                            "extra": {"requested_id": asked, "found": False}})
                continue
            ext = p.get("externalIds") or {}
            venue = (p.get("publicationVenue") or {}).get("name") or p.get("venue")
            journal = (p.get("journal") or {}).get("name")
            dblp = ext.get("DBLP") if not (ext.get("DBLP") or "").startswith("journals/corr/") else None
            links = []
            if rec["ids"]["doi"]:
                links.append({"kind": "doi", "url": "https://doi.org/" + rec["ids"]["doi"]})
            if ext.get("ACL"):
                links.append({"kind": "acl-anthology", "url": "https://aclanthology.org/%s/" % ext["ACL"]})
            if dblp:
                links.append({"kind": "dblp-record", "url": "https://dblp.org/rec/%s.html" % dblp})
            oa = (p.get("openAccessPdf") or {}).get("url")
            if oa and "arxiv.org" not in oa:
                links.append({"kind": "open-access-pdf", "url": oa})
            published = bool(links) or not _arxiv_only(venue) or not _arxiv_only(journal)
            rec["extra"].update({
                "requested_id": asked, "found": True, "published": published,
                "published_venue": None if _arxiv_only(venue) else venue,
                "journal": None if _arxiv_only(journal) else journal,
                "links": links, "best_link": links[0]["url"] if links else None,
                "arxiv_abs": "https://arxiv.org/abs/" + rec["ids"]["arxiv"] if rec["ids"]["arxiv"] else None,
            })
            out.append(rec)
    return out


def _edges(record_id, kind, limit):
    """kind 'references' -> citedPaper, 'citations' -> citingPaper."""
    inner = "citedPaper" if kind == "references" else "citingPaper"
    fl = "contexts,intents,isInfluential," + ",".join(inner + "." + f for f in S2_FIELDS.split(","))
    out, offset = [], 0
    while offset < limit:
        page = min(1000, limit - offset)
        res = http("s2", S2_GRAPH + "/paper/%s/%s" % (urllib.parse.quote(s2_ref(record_id), safe=":/"), kind),
                   {"fields": fl, "limit": page, "offset": offset}, allow_404=True)
        if not res:
            break
        for e in res.get("data") or []:
            rec = s2_record(e.get(inner), {
                "contexts": [c[:300] for c in (e.get("contexts") or [])[:3]],
                "intents": e.get("intents") or [],
                "is_influential": e.get("isInfluential"),
            })
            if rec:
                out.append(rec)
        if res.get("next") is None:
            break
        offset = res["next"]
        if offset + 1 > 9999:  # S2 rejects offset + limit >= 10000
            break
    return out


def s2_references(a):
    return _edges(a.id, "references", a.limit)


def s2_citations(a):
    recs = _edges(a.id, "citations", a.limit)
    recs.sort(key=lambda r: r["year"] or 0, reverse=True)
    return recs


def s2_recommend(a):
    def to_s2(id_list):
        return [r["ids"]["s2"] for r in s2_batch_ids(id_list, False) if r["ids"]["s2"]]
    pos = to_s2(a.positive)
    neg = to_s2(a.negative or [])
    if not pos:
        sys.exit("none of the positive ids were found in Semantic Scholar")
    res = http("s2", S2_RECS + "/papers", {"fields": fields(True), "limit": min(a.limit, 500)},
               body={"positivePaperIds": pos, "negativePaperIds": neg})
    return [r for r in (s2_record(p) for p in res.get("recommendedPapers") or []) if r]


# ---------------------------------------------------------------- arXiv

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def parse_arxiv_feed(xml_text):
    root = ET.fromstring(xml_text)
    out = []
    for e in root.findall(ATOM + "entry"):
        id_url = (e.findtext(ATOM + "id") or "").strip()
        if "/abs/" not in id_url:
            continue
        aid = strip_arxiv_version(id_url.split("/abs/", 1)[1])
        title = " ".join((e.findtext(ATOM + "title") or "").split())
        abstract = " ".join((e.findtext(ATOM + "summary") or "").split())
        published = e.findtext(ATOM + "published") or ""
        year = int(published[:4]) if published[:4].isdigit() else None
        authors = author_string([a.findtext(ATOM + "name") for a in e.findall(ATOM + "author")])
        doi = clean_doi(e.findtext(ARXIV_NS + "doi"))
        journal = e.findtext(ARXIV_NS + "journal_ref")
        cats = [c.get("term") for c in e.findall(ATOM + "category")]
        out.append(record({"arxiv": aid, "doi": doi}, title, year, journal or "arXiv", authors,
                          abstract, "https://arxiv.org/abs/" + aid, None,
                          {"published": published[:10], "categories": cats}))
    return out


def arxiv_query_string(q, raw):
    if raw or ":" in q:
        return q
    words = [w for w in q.split() if w]
    return " AND ".join("all:" + w for w in words)


def arxiv_search(a):
    q = arxiv_query_string(a.query, a.raw)
    if a.category:
        q = "(%s) AND cat:%s" % (q, a.category)
    if a.since:
        start = dt.date.fromisoformat(a.since).strftime("%Y%m%d") + "0000"
        end = dt.date.today().strftime("%Y%m%d") + "2359"
        q = "(%s) AND submittedDate:[%s TO %s]" % (q, start, end)
    params = {"search_query": q, "start": 0, "max_results": min(a.max, 200)}
    if a.sort == "date":
        params.update(sortBy="submittedDate", sortOrder="descending")
    else:
        params.update(sortBy="relevance", sortOrder="descending")
    return parse_arxiv_feed(http("arxiv", ARXIV_API, params, raw=True))


# ---------------------------------------------------------------- DBLP

def _as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def parse_dblp(res):
    hits = (((res or {}).get("result") or {}).get("hits") or {}).get("hit")
    out = []
    for h in _as_list(hits):
        info = h.get("info") or {}
        title = (info.get("title") or "").rstrip(".")
        names = [a.get("text") if isinstance(a, dict) else a
                 for a in _as_list((info.get("authors") or {}).get("author"))]
        venue = info.get("venue")
        if isinstance(venue, list):
            venue = ", ".join(venue)
        year = int(info["year"]) if str(info.get("year", "")).isdigit() else None
        doi = clean_doi(info.get("doi"))
        arxiv = None
        for link in _as_list(info.get("ee")):
            if isinstance(link, str) and "arxiv.org/abs/" in link:
                arxiv = strip_arxiv_version(link.split("arxiv.org/abs/", 1)[1])
        if (venue or "").lower() == "corr" and not arxiv and doi and doi.startswith("10.48550/arxiv."):
            arxiv = doi.split("arxiv.", 1)[1]
        out.append(record({"doi": doi, "arxiv": arxiv, "dblp": info.get("key")}, title, year, venue,
                          author_string(names), None, info.get("url"), None, {"type": info.get("type")}))
    return out


def dblp_search(a):
    res = http("dblp", DBLP_API, {"q": a.query, "format": "json", "h": min(a.max, 1000)})
    return parse_dblp(res)


def dblp_bib(a):
    text = http("dblp", "https://dblp.org/rec/%s.bib" % a.key, raw=True)
    sys.stdout.write(text)
    return None


# ---------------------------------------------------------------- references of interest

def resolve_refs(a):
    data = read_json(a.expand_file)
    refs = data.get("references_of_interest") or []
    known = []
    if a.citing_id:
        try:
            known = _edges(a.citing_id, "references", 1000)
        except SystemExit:
            known = []
    by_title = {norm_title(r["title"]): r for r in known if r.get("title")}
    resolved, unresolved = [], []
    for ref in refs:
        title = ref.get("title") or ""
        seen = ref.get("ids_seen") or {}
        rec = None
        if seen.get("doi"):
            got = s2_paper(argparse.Namespace(id="doi:" + clean_doi(seen["doi"]), abstract=True))
            rec = got[0] if got else None
        if not rec and seen.get("arxiv"):
            got = s2_paper(argparse.Namespace(id="arxiv:" + strip_arxiv_version(seen["arxiv"]), abstract=True))
            rec = got[0] if got else None
        if not rec and title:
            rec = by_title.get(norm_title(title))
            if not rec:
                best = max(known, key=lambda r: title_similarity(title, r["title"]), default=None)
                if best and title_similarity(title, best["title"]) >= 0.92:
                    rec = best
        if not rec and title:
            m = s2_match_title(title)
            if m and m["extra"]["title_similarity"] >= 0.9:
                rec = m
        if rec:
            rec = json.loads(json.dumps(rec))
            rec["extra"].update({"cited_for": ref.get("cited_for"), "relevant_to": ref.get("relevant_to"),
                                 "why": ref.get("why"), "ref_text": ref.get("ref_text")})
            resolved.append(rec)
        else:
            unresolved.append({"title": title, "ref_text": ref.get("ref_text"), "year": ref.get("year")})
    return {"records": resolved, "unresolved": unresolved}


# ---------------------------------------------------------------- CLI

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_text):
        sp = sub.add_parser(name, help=help_text)
        sp.set_defaults(fn=fn)
        sp.add_argument("--out", help="write JSON to this file instead of stdout")
        return sp

    sp = add("arxiv-search", arxiv_search, "search arXiv")
    sp.add_argument("--query", required=True, help="plain words (ANDed) or arXiv query syntax")
    sp.add_argument("--max", type=int, default=25)
    sp.add_argument("--since", help="YYYY-MM-DD: only papers submitted since this date")
    sp.add_argument("--sort", choices=["relevance", "date"], default="relevance")
    sp.add_argument("--category", help="arXiv category, e.g. cs.LG")
    sp.add_argument("--raw", action="store_true", help="pass --query to arXiv unchanged")

    sp = add("s2-search", s2_search, "Semantic Scholar relevance search (with abstracts)")
    sp.add_argument("--query", required=True)
    sp.add_argument("--limit", type=int, default=25)
    sp.add_argument("--year", help="e.g. 2019- or 2018-2024")
    sp.add_argument("--fields-of-study", help="e.g. 'Computer Science'")

    sp = add("s2-match", s2_match, "best Semantic Scholar match for a title (check title_similarity)")
    sp.add_argument("--title", required=True)

    sp = add("s2-paper", s2_paper, "one paper by id")
    sp.add_argument("--id", required=True)
    sp.add_argument("--abstract", action="store_true")

    sp = add("s2-batch", s2_batch, "many papers by id (up to 500 per request)")
    sp.add_argument("--ids", nargs="*")
    sp.add_argument("--ids-file", help="file with one id per line")
    sp.add_argument("--abstract", action="store_true")

    sp = add("published-links", published_links,
             "for fetch lists: does each paper have a version outside arXiv, and links to it "
             "(extra: published, published_venue, journal, links, best_link, arxiv_abs)")
    sp.add_argument("--ids", nargs="*")
    sp.add_argument("--ids-file", help="file with one id per line")

    sp = add("s2-references", s2_references, "papers this paper cites, with citation contexts")
    sp.add_argument("--id", required=True)
    sp.add_argument("--limit", type=int, default=1000)

    sp = add("s2-citations", s2_citations, "papers citing this paper, newest first, with contexts")
    sp.add_argument("--id", required=True)
    sp.add_argument("--limit", type=int, default=200)

    sp = add("s2-recommend", s2_recommend, "recommendations from positive (and negative) example papers")
    sp.add_argument("--positive", nargs="+", required=True)
    sp.add_argument("--negative", nargs="*")
    sp.add_argument("--limit", type=int, default=50)

    sp = add("dblp-search", dblp_search, "search DBLP (no abstracts)")
    sp.add_argument("--query", required=True)
    sp.add_argument("--max", type=int, default=25)

    sp = add("dblp-bib", dblp_bib, "print DBLP's BibTeX for a DBLP key")
    sp.add_argument("--key", required=True)

    sp = add("resolve-refs", resolve_refs,
             "resolve a paper-reader result's references_of_interest to records")
    sp.add_argument("--expand-file", required=True)
    sp.add_argument("--citing-id", help="id of the paper whose references these are")

    a = p.parse_args()
    result = a.fn(a)
    if result is not None:
        emit(result, a.out)
        if isinstance(result, dict) and result.get("unresolved"):
            print("unresolved references: %d (see 'unresolved' in the output)" % len(result["unresolved"]),
                  file=sys.stderr)


if __name__ == "__main__":
    main()
