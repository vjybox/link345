#!/usr/bin/env python3
"""Merge cross-checked baseline metadata (HQ + core facts) into the repo.

Input: a pipe-delimited text file with a HEADER ROW naming the columns, then
one row per company. Column order is free; recognised headers:

    Name | Type | HQ City | HQ Country | Founded | Ownership | Website | Production base(s) | One-liner

Any column may be omitted or left blank. "Name" is matched against
data/companies.txt with the same cleaned-name + prefix-resolve logic build.py
uses, so "CATL" matches "CATL (Contemporary Amperex Technology Co., Limited)".

Routing:
  - Website / HQ City / HQ Country -> data/companies.txt line (url / city= / country=)
  - Type / Founded / Ownership / One-liner / Production base(s) -> metadata,
    merged INTO the entity's existing record (whatever shard it lives in), or a
    new minimal record in data/metadata/15-baseline.json if it has none.

Safety: FILL-GAP by default -- only sets a field that is currently empty, so a
bulk pass never clobbers the hand-curated profiles. Pass --overwrite to let the
new values win. New records use the full cleaned name as an exact-match key to
avoid the shortest-prefix collision documented in METADATA.md.

Usage:
    python3 build.py                              # refresh dist/directory.json
    python3 tools/apply_locations.py data/baseline-batch1.txt
    python3 tools/apply_locations.py data/batch.txt --overwrite   # force
    python3 build.py                              # apply + check [warn] lines
"""
import argparse
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPANIES = ROOT / "data" / "companies.txt"
METADATA_DIR = ROOT / "data" / "metadata"
NEW_SHARD = METADATA_DIR / "15-baseline.json"
DIRECTORY = ROOT / "dist" / "directory.json"

# header alias -> canonical field
HEADER_ALIASES = {
    "name": {"name", "company name", "company", "entity"},
    "type": {"type", "entity type"},
    "city": {"hq city", "city", "headquarters city", "hq"},
    "country": {"hq country", "country", "headquarters country"},
    "founded": {"founded", "founded year", "year founded"},
    "ownership": {"ownership", "ownership type"},
    "website": {"website", "url", "official site", "official url", "site"},
    "production_base": {"production base(s)", "production bases", "production base",
                         "production", "manufacturing"},
    "one_liner": {"one-liner", "one liner", "oneliner", "summary", "description",
                   "one line", "tagline"},
}
COMPANIES_FIELDS = {"website", "city", "country"}
META_FIELDS = {"type", "founded", "ownership", "one_liner", "production_base"}
TYPE_ENUM = {"Corporate", "Facility", "People", "Research", "Institution", "Media"}


def clean_name(name):
    base = re.sub(r"\([^)]*\)", " ", name)
    base = re.split(r"\s[-/]\s", base)[0]
    return re.sub(r"\s+", " ", base).strip().lower()


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def canon(header):
    h = norm(header)
    for key, aliases in HEADER_ALIASES.items():
        if h in aliases:
            return key
    return None


def parse_input(path):
    lines = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        sys.exit("input file is empty.")
    header = [canon(c) for c in lines[0].split("|")]
    if "name" not in header:
        sys.exit("first non-comment line must be a header row naming the columns "
                 "(it needs a 'Name' column). See data/LOCATION_PROMPT.md.")
    rows = []
    for ln in lines[1:]:
        cells = [c.strip() for c in ln.split("|")]
        rec = {}
        for i, val in enumerate(cells):
            if i < len(header) and header[i] and val:
                rec[header[i]] = val
        if rec.get("name"):
            rows.append(rec)
    return header, rows


def main():
    ap = argparse.ArgumentParser(description="Merge baseline metadata into the repo.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("input", help="pipe-delimited file with a header row")
    ap.add_argument("--overwrite", action="store_true",
                    help="let input values win over existing non-empty data")
    ap.add_argument("--dry-run", action="store_true", help="report without writing")
    args = ap.parse_args()

    if not DIRECTORY.exists():
        sys.exit("dist/directory.json not found -- run `python3 build.py` first.")
    payload = json.loads(DIRECTORY.read_text("utf-8"))
    entries = payload["entries"]
    by_norm = {}
    for e in entries:
        by_norm.setdefault(norm(clean_name(e["n"])), e)

    def resolve(key):
        # clean_name first so an input copied straight from the dataset
        # ("GAC Group (Aion)") strips to the same token as the entry ("gac group").
        key = norm(clean_name(key))
        if key in by_norm:
            return by_norm[key]
        hit = hit_cn = None
        for cn, e in by_norm.items():
            if cn.startswith(key + " ") and (hit is None or len(cn) < len(hit_cn)):
                hit, hit_cn = e, cn
        return hit

    # existing metadata + owner map (so meta fields merge into the same record)
    shard_data, key_owner = {}, {}
    for f in sorted(glob.glob(str(METADATA_DIR / "*.json"))):
        d = json.loads(Path(f).read_text("utf-8"))
        shard_data[f] = d
        for k in d:
            if k.startswith("_"):
                continue
            e = resolve(k)
            if e:
                key_owner[e["eid"]] = (f, k)

    header, rows = parse_input(args.input)
    used = sorted({h for h in header if h and h != "name"})
    print(f"columns detected: {', '.join(used) or '(none)'}")
    print(f"input rows: {len(rows)}   mode: {'OVERWRITE' if args.overwrite else 'fill-gap'}")

    misses = []
    companies_patch = {}   # eid -> {website,city,country}
    new_records = {}
    field_counts = {}

    def bump(f):
        field_counts[f] = field_counts.get(f, 0) + 1

    for row in rows:
        e = resolve(row["name"])
        if not e:
            misses.append(row["name"]); continue
        # company-line fields
        cp = {}
        for fld in COMPANIES_FIELDS:
            if fld in row:
                cp[fld] = row[fld]
        if cp:
            companies_patch[e["eid"]] = cp
        # metadata fields
        meta_in = {}
        for fld in META_FIELDS:
            if fld not in row:
                continue
            v = row[fld]
            if fld == "type" and v not in TYPE_ENUM:
                continue
            if fld == "founded":
                if not re.fullmatch(r"\d{4}", v):
                    continue
                v = int(v)
            meta_in[fld] = v
        if meta_in:
            if e["eid"] in key_owner:
                f, k = key_owner[e["eid"]]
                rec = shard_data[f][k]
            else:
                key = norm(clean_name(e["n"]))
                rec = new_records.setdefault(key, {"type": e.get("et", "Corporate")})
            for fld, v in meta_in.items():
                if args.overwrite or rec.get(fld) in (None, ""):
                    rec[fld] = v; bump(fld)

    print(f"resolved: {len(rows) - len(misses)}   unmatched: {len(misses)}")
    for fld in sorted(field_counts):
        print(f"  metadata {fld}: {field_counts[fld]} set")
    if misses:
        mp = Path(args.input).with_suffix(".misses.txt")
        mp.write_text("\n".join(misses), encoding="utf-8")
        print(f"  unmatched names -> {mp}")
        for m in misses[:15]:
            print("  MISS:", m)
        if len(misses) > 15:
            print(f"  ... and {len(misses)-15} more")

    if args.dry_run:
        print("(dry run -- nothing written)")
        return

    # --- patch companies.txt (fill-gap unless --overwrite) ---
    id_to_eid = {e["i"]: e["eid"] for e in entries}
    entry_re = re.compile(r"^(\d+\.\s*)(.+?)\s*$")
    out, patched = [], 0
    for raw in COMPANIES.read_text(encoding="utf-8").splitlines():
        m = entry_re.match(raw)
        if m:
            prefix, text = m.groups()
            num = int(re.match(r"(\d+)", prefix).group(1))
            cp = companies_patch.get(id_to_eid.get(num))
            if cp:
                base, *extras = [p.strip() for p in text.split("|")]
                cur_url = cur_country = cur_city = ""
                kept = []
                for x in extras:
                    xl = x.lower()
                    if x.startswith("http"):
                        cur_url = x
                    elif xl.startswith("country="):
                        cur_country = x.split("=", 1)[1].strip()
                    elif xl.startswith("city="):
                        cur_city = x.split("=", 1)[1].strip()
                    else:
                        kept.append(x)   # logo= and anything else, preserved

                def pick(new, cur):
                    return new if new and (args.overwrite or not cur) else cur
                url = pick(cp.get("website", ""), cur_url)
                country = pick(cp.get("country", ""), cur_country)
                city = pick(cp.get("city", ""), cur_city)
                pieces = [base]
                if url:
                    pieces.append(url)
                if country:
                    pieces.append(f"country={country}")
                if city:
                    pieces.append(f"city={city}")
                pieces += kept
                out.append(prefix + " | ".join(pieces))
                patched += 1
                continue
        out.append(raw)
    COMPANIES.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"data/companies.txt: patched {patched} lines")

    for f, d in shard_data.items():
        Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if new_records:
        doc = {"_doc": "Minimal baseline records for entities with no other curated "
                       "profile yet (type/one_liner/founded/ownership/production_base). "
                       "See data/LOCATION_PROMPT.md and METADATA.md."}
        if NEW_SHARD.exists():
            doc = json.loads(NEW_SHARD.read_text("utf-8"))
            doc.update(new_records)
        else:
            doc.update(new_records)
        NEW_SHARD.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{NEW_SHARD}: {len(new_records)} new minimal records")

    print("Run `python3 build.py` to apply and check for [warn] lines.")


if __name__ == "__main__":
    main()
