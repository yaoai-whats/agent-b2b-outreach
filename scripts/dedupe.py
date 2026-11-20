#!/usr/bin/env python3
"""Deduplicate a leads file on the company domain.

Rows are grouped by `domain` (lowercased, scheme and leading "www."
stripped). Rows without a domain fall back to company name plus country.
For each duplicate group, the surviving row is the one with the most
non-empty fields; the other rows contribute any emails the survivor does
not already have (merged, original order kept, no duplicates), and no other
field is overwritten silently: conflicting values are listed in the
report for a human to resolve.

Default is a dry run: the report is printed and the file is untouched.
Add --write to save the merged rows back.

    python3 dedupe.py --leads data/leads.jsonl
    python3 dedupe.py --leads data/leads.jsonl --write
"""
import argparse
import json
import sys


def row_key(row):
    domain = (row.get("domain") or "").strip().lower()
    for prefix in ("https://", "http://"):
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
    domain = domain.rstrip("/")
    if domain.startswith("www."):
        domain = domain[4:]
    if domain:
        return "domain:" + domain
    return "name:" + (row.get("company", "").strip().lower()
                      + "|" + row.get("country", "").strip().lower())


def completeness(row):
    return sum(1 for v in row.values()
               if v not in ("", None, [], False))


def main():
    parser = argparse.ArgumentParser(description="Deduplicate leads by domain.")
    parser.add_argument("--leads", default="data/leads.jsonl")
    parser.add_argument("--write", action="store_true",
                        help="Write the merged rows back to the file.")
    args = parser.parse_args()

    with open(args.leads, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]

    groups = {}
    order = []
    for row in rows:
        key = row_key(row)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)

    merged_rows = []
    dup_groups = 0
    removed = 0
    conflicts = []
    for key in order:
        group = groups[key]
        if len(group) == 1:
            merged_rows.append(group[0])
            continue
        dup_groups += 1
        removed += len(group) - 1
        survivor = max(group, key=completeness)
        emails = list(survivor.get("emails") or [])
        for other in group:
            if other is survivor:
                continue
            for addr in other.get("emails") or []:
                if addr not in emails:
                    emails.append(addr)
            for field, value in other.items():
                if field == "emails":
                    continue
                kept = survivor.get(field)
                if value not in ("", None, []) and kept not in ("", None, []) \
                        and value != kept:
                    conflicts.append(
                        f"{key}: field '{field}' kept {kept!r}, "
                        f"dropped {value!r}")
        survivor["emails"] = emails
        merged_rows.append(survivor)

    print(f"rows in: {len(rows)}")
    print(f"duplicate groups: {dup_groups}")
    print(f"rows removed: {removed}")
    print(f"rows out: {len(merged_rows)}")
    for line in conflicts:
        print(f"conflict (kept most complete row's value): {line}")
    if args.write and removed:
        with open(args.leads, "w", encoding="utf-8") as fh:
            for row in merged_rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"wrote merged rows back to {args.leads}")
    elif removed:
        print("dry run: file unchanged (add --write to save)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
