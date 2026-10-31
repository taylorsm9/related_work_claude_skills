#!/usr/bin/env python3
"""Concatenate named sections of Markdown files into one digest (synthesis stage). Standard library only.

  digest.py --title T --section A [--section B ...] --out F FILE...
      One block per FILE, headed by its citekey (the file name without .md and without a
      trailing -related), holding the sections whose heading text is A or B, in file order.
      A section runs to the next heading of the same or a higher level.
      Mechanical: no text is changed. Prints a one-line count; exit 1 if a file lacks a section.
"""

import argparse
import os
import re
import sys

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")


def sections(text, names):
    """{name: section text including its heading} for each heading whose text is in names."""
    found = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = HEADING.match(lines[i])
        if m and m.group(2) in names:
            level = len(m.group(1))
            j = i + 1
            while j < len(lines):
                n = HEADING.match(lines[j])
                if n and len(n.group(1)) <= level:
                    break
                j += 1
            found[m.group(2)] = "\n".join(lines[i:j]).rstrip()
            i = j
        else:
            i += 1
    return found


def citekey(path):
    name = os.path.basename(path)
    name = name[:-3] if name.endswith(".md") else name
    return name[:-len("-related")] if name.endswith("-related") else name


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--title", required=True)
    ap.add_argument("--section", action="append", required=True, help="heading text; repeat for more")
    ap.add_argument("--out", required=True)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    names = a.section
    blocks, missing = [], []
    for path in sorted(a.files):
        with open(path, encoding="utf-8") as f:
            found = sections(f.read(), set(names))
        missing += ["%s: %s" % (path, n) for n in names if n not in found]
        blocks.append("## %s\n\n%s" % (citekey(path), "\n\n".join(found[n] for n in names if n in found)))
    head = ("# %s\n\nMechanical concatenation of the sections %s of %d files, one block per paper. "
            "The full text of each is in its own file.\n" % (a.title, ", ".join("*%s*" % n for n in names), len(a.files)))
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(head + "\n\n" + "\n\n".join(blocks) + "\n")
    words = sum(len(b.split()) for b in blocks)
    print("%s: %d files, about %d words%s" % (a.out, len(a.files), words,
                                               ", %d missing sections" % len(missing) if missing else ""))
    for m in missing:
        print("missing " + m, file=sys.stderr)
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
