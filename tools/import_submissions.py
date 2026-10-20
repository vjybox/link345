#!/usr/bin/env python3
"""Turn reviewed Submit-a-company CSV rows into ready-to-merge entries.

Input: the CSV downloaded from /admin/submissions.csv (the self-hosted
Submit form's admin dashboard -- see server/app.py and DEPLOY-SYNOLOGY.md).
Trim the CSV to just the rows you've reviewed and want to import before
running this (or use --status to filter) -- this tool does not know which
submissions you've approved, only what's in the file you hand it.

For each row it:
  - skips (with a reason, written to a review file -- never silently
    dropped) anything that looks like a duplicate of an existing entry,
    is missing a company name, or has no confident category match;
  - otherwise appends a new numbered line to the matched category's block
    in data/companies.txt (new entries get the next free global ID -- IDs
    are unique across the whole file, not per-category) and a minimal
    metadata record (just one_liner, from the submitted description) to
    data/metadata/16-submissions.json, keyed by the new entry's full
    cleaned name (an exact-match key, so it can't collide with a
    same-named plant/entity elsewhere -- see METADATA.md).

"Related companies & relationship" text is free-form and NOT auto-
converted into a relationships.json edge (too unstructured to parse
reliably) -- it's surfaced in the review file so you can add it by hand
if it checks out.

Usage:
    python3 build.py                                  # refresh dist/directory.json
    python3 tools/import_submissions.py submissions.csv
    python3 tools/import_submissions.py submissions.csv --status pending
    python3 build.py                                  # apply + check [warn] lines
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPANIES = ROOT / "data" / "companies.txt"
METADATA_DIR = ROOT / "data" / "metadata"
NEW_SHARD = METADATA_DIR / "16-submissions.json"
DIRECTORY = ROOT / "dist" / "directory.json"


def clean_name(name):
    base = re.sub(r"\([^)]*\)", " ", name)
    base = re.split(r"\s[-/]\s", base)[0]
    return re.sub(r"\s+", " ", base).strip().lower()


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def main():
    ap = argparse.ArgumentParser(description="Import reviewed Submit-form rows into the repo.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("csv_file")
    ap.add_argument("--status", help="only import rows with this status column value "
                                      "(e.g. 'approved', if you've been editing the CSV by hand)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not DIRECTORY.exists():
        sys.exit("dist/directory.json not found -- run `python3 build.py` first.")
    payload = json.loads(DIRECTORY.read_text("utf-8"))
    entries = payload["entries"]

    by_norm = {}
    for e in entries:
        by_norm.setdefault(norm(clean_name(e["n"])), e)

    def resolve(key):
        key = norm(clean_name(key))
        if key in by_norm:
            return by_norm[key]
        hit = hit_cn = None
        for cn, e in by_norm.items():
            if cn.startswith(key + " ") and (hit is None or len(cn) < len(hit_cn)):
                hit, hit_cn = e, cn
        return hit

    # category name -> category id, from the live payload's tree
    cat_id_by_name = {}
    for sector_cats in payload["tree"].values():
        for c in sector_cats:
            cat_id_by_name[norm(c["name"])] = (c["id"], c["name"])

    rows = list(csv.DictReader(open(args.csv_file, encoding="utf-8")))
    if args.status:
        rows = [r for r in rows if r.get("status", "").strip().lower() == args.status.lower()]
    print(f"rows to process: {len(rows)}")

    imported, skipped = [], []
    next_id = max((e["i"] for e in entries), default=0) + 1
    new_lines_by_cat = {}   # cat_id -> [line, ...]
    new_meta = {}

    for row in rows:
        name = (row.get("company_name") or "").strip()
        if not name:
            skipped.append((row.get("id", "?"), "NO_NAME", "missing company_name")); continue

        existing = resolve(name)
        if existing:
            skipped.append((row.get("id", "?"), "DUPLICATE",
                             f"matches existing entry {existing['n']!r} ({existing['eid']})")); continue

        cat_raw = (row.get("category") or "").strip()
        cat_match = cat_id_by_name.get(norm(cat_raw)) if cat_raw else None
        if not cat_match:
            skipped.append((row.get("id", "?"), "NO_CATEGORY",
                             f"category {cat_raw!r} didn't match any of the 30 -- place by hand")); continue
        cat_id, cat_name = cat_match

        url = (row.get("official_url") or "").strip()
        country = (row.get("country") or "").strip()
        parts = [f"{next_id}. {name}"]
        if url:
            parts.append(url)
        if country:
            parts.append(f"country={country}")
        line = " | ".join(parts)

        new_lines_by_cat.setdefault(cat_id, []).append(line)

        key = norm(clean_name(name))
        one_liner = (row.get("description") or "").strip()[:200]
        rec = {"type": "Corporate"}
        if one_liner:
            rec["one_liner"] = one_liner
        new_meta[key] = rec

        note = ""
        rel = (row.get("related_companies") or "").strip()
        if rel:
            note = f" -- relationship note (add to relationships.json by hand if valid): {rel!r}"
        imported.append((next_id, name, cat_name, note))
        next_id += 1

    print(f"to import: {len(imported)}   skipped: {len(skipped)}")
    for sid, reason, detail in skipped:
        print(f"  SKIP [{reason}] row {sid}: {detail}")
    for nid, name, cat_name, note in imported:
        print(f"  + #{nid} {name!r} -> {cat_name}{note}")

    if args.dry_run:
        print("(dry run -- nothing written)")
        return
    if not imported:
        print("Nothing to import.")
        return

    # --- insert new lines at the end of each matched category's block ---
    lines = COMPANIES.read_text(encoding="utf-8").splitlines()
    out = []
    current_cat = None
    for i, raw in enumerate(lines):
        m = re.match(r"^##\s*(\d+)\s*\|", raw.strip())
        if m:
            # flush pending new lines for the category we're LEAVING
            if current_cat in new_lines_by_cat:
                out.extend(new_lines_by_cat.pop(current_cat))
            current_cat = int(m.group(1))
        out.append(raw)
    if current_cat in new_lines_by_cat:  # last category in the file
        out.extend(new_lines_by_cat.pop(current_cat))
    COMPANIES.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"data/companies.txt: appended {len(imported)} lines")

    if new_meta:
        doc = {"_doc": "Minimal records for companies added via the self-hosted Submit "
                       "form (tools/import_submissions.py). See DEPLOY-SYNOLOGY.md."}
        if NEW_SHARD.exists():
            doc = json.loads(NEW_SHARD.read_text("utf-8"))
        doc.update(new_meta)
        NEW_SHARD.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{NEW_SHARD}: {len(new_meta)} new minimal records")

    if skipped:
        review_path = Path(args.csv_file).with_suffix(".review.txt")
        review_path.write_text(
            "\n".join(f"[{r}] row {sid}: {d}" for sid, r, d in skipped), encoding="utf-8")
        print(f"skipped rows written to {review_path} for manual handling")

    print("Run `python3 build.py` to apply and check for [warn] lines.")


if __name__ == "__main__":
    main()
