#!/usr/bin/env python3
"""Citation keys in LaTeX files. Standard library only.

  cites.py keys FILE                       keys with counts
  cites.py compare BEFORE AFTER            exit 1 if the keys or counts differ
  cites.py check-bib FILE --bib refs.bib   exit 1 if a cited key has no entry
  cites.py sentences FILE [--out F]        {key: [{"line": n, "sentence": "..."}]}
                                           (line = where it starts in FILE; whitespace collapsed)
"""

import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import emit  # noqa: E402
from bib import parse_bib  # noqa: E402

# \cite, \citep, \citet, \citealp, \citeauthor, \parencite, \textcite, \autocite, \footcite, \Cite… (+ starred)
CITE = re.compile(r"\\(?:[Cc]ite\w*|parencite|textcite|autocite|footcite|smartcite)\*?"
                  r"(?:\s*\[[^\]]*\]){0,2}\s*\{([^}]*)\}")


def blank(m):
    """Replace a match with spaces of the same length, keeping newlines (offsets stay valid)."""
    return re.sub(r"[^\n]", " ", m.group(0))


def read_tex(path):
    """File text with % comments blanked out (same length, so line numbers still match the file)."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return re.sub(r"(?<!\\)%.*", blank, text)


def keys_in(text):
    keys = []
    for m in CITE.finditer(text):
        keys += [k.strip() for k in m.group(1).split(",") if k.strip()]
    return keys


def sentences(text):
    """[(line, sentence)]: line is the 1-based line in the file where the sentence starts;
    the sentence has its whitespace collapsed to single spaces."""
    body = re.sub(r"\\(section|subsection|subsubsection|paragraph|label)\*?\{[^}]*\}", blank, text)
    # Protect common abbreviations (same length) before splitting.
    body = re.sub(r"\b(et al|e\.g|i\.e|cf|vs|Fig|Sec|Eq|resp)\.", lambda m: m.group(0).replace(".", "\0"), body)
    out, start = [], 0
    bounds = [m.start() for m in re.finditer(r"(?<=[.!?])\s+(?=[A-Z\\])|\n\s*\n", body)] + [len(body)]
    for end in bounds:
        chunk = body[start:end]
        stripped = chunk.lstrip()
        if stripped.strip():
            first = start + (len(chunk) - len(stripped))
            line = text.count("\n", 0, first) + 1
            out.append((line, re.sub(r"\s+", " ", stripped.replace("\0", ".")).strip()))
        start = end
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("keys")
    sp.add_argument("file")
    sp = sub.add_parser("compare")
    sp.add_argument("before")
    sp.add_argument("after")
    sp = sub.add_parser("check-bib")
    sp.add_argument("file")
    sp.add_argument("--bib", required=True)
    sp = sub.add_parser("sentences")
    sp.add_argument("file")
    sp.add_argument("--out")
    a = p.parse_args()

    if a.cmd == "keys":
        for k, n in sorted(collections.Counter(keys_in(read_tex(a.file))).items()):
            print("%s %d" % (k, n))
    elif a.cmd == "compare":
        before = collections.Counter(keys_in(read_tex(a.before)))
        after = collections.Counter(keys_in(read_tex(a.after)))
        if before == after:
            print("same keys and counts: %d keys, %d citations" % (len(after), sum(after.values())))
            return
        for k in sorted(set(before) | set(after)):
            if before[k] != after[k]:
                print("%s: %d before, %d after" % (k, before[k], after[k]))
        sys.exit(1)
    elif a.cmd == "check-bib":
        with open(a.bib, encoding="utf-8") as f:
            known = {e["key"] for e in parse_bib(f.read())}
        cited = set(keys_in(read_tex(a.file)))
        missing = sorted(cited - known)
        if missing:
            print("cited but not in %s: %s" % (a.bib, ", ".join(missing)))
            sys.exit(1)
        print("all %d cited keys are in %s" % (len(cited), a.bib))
    elif a.cmd == "sentences":
        result = collections.OrderedDict()
        for line, s in sentences(read_tex(a.file)):
            for k in dict.fromkeys(keys_in(s)):
                result.setdefault(k, []).append({"line": line, "sentence": s})
        if a.out:
            d = os.path.dirname(a.out)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(a.out, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print("wrote %s (%d keys)" % (a.out, len(result)))
        else:
            emit(result)


if __name__ == "__main__":
    main()
