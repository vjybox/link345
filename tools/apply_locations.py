#!/usr/bin/env python3
"""Merge cross-checked HQ location + production-base data into the repo.

Input: a pipe-delimited text file, one header line then one line per company:

    Company Name | HQ City | HQ Country | Production base(s)
    CATL | Ningde | China | Ningde, Yibin & Liyang (China); Debrecen (Hungary)

"Company Name" is matched against data/companies.txt using the same
cleaned-name + prefix-resolve logic as build.py, so "CATL" matches the full
entry "CATL (Contemporary Amperex Technology Co., Limited)". Any column may
be left blank (e.g. no production base known) -- blank fields are skipped,
never used to erase existing data.

Usage:
    python3 build.py                        # refresh dist/directory.json
    python3 tools/apply_locations.py data/locations-batch1.txt
    python3 build.py                        # rebuild with the new data

Safety: if an entity already has a metadata record (in any shard),
production_base is merged INTO that existing record -- never written to a
new key, which would silently replace (not merge with) the existing profile
per build.py's shard-loading semantics. Entities with no prior metadata get
a new minimal record in data/metadata/15-locations.json, keyed by their full
cleaned name (exact match, to avoid the shortest-prefix collision bug
documented in METADATA.md).
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
NEW_SHARD = METADATA_DIR / "15-locations.json"
DIRECTORY = ROOT / "dist" / "directory.json"


def clean_name(name):
    base = re.sub(r"\([^)]*\)", " ", name)
    base = re.split(r"\s[-/]\s", base)[0]
    return re.sub(r"\s+", " ", base).strip().lower()


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def parse_input(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if parts[0].lower() in ("company name", "company", "name"):
            continue  # header row
        name = parts[0]
        city = parts[1] if len(parts) > 1 else ""
        country = parts[2] if len(parts) > 2 else ""
        prod = parts[3] if len(parts) > 3 else ""
        if not name:
            continue
        rows.append({"name": name, "city": city, "country": country, "production_base": prod})
    return rows


def main():
    ap = argparse.ArgumentParser(
        description="Merge cross-checked HQ/production-base location data into the repo.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("input", help="pipe-delimited location file")
    ap.add_argument("--dry-run", action="store_true", help="report matches without writing anything")
    args = ap.parse_args()

    if not DIRECTORY.exists():
        sys.exit("dist/directory.json not found -- run `python3 build.py` first.")
    payload = json.loads(DIRECTORY.read_text("utf-8"))
    entries = payload["entries"]

    by_norm = {}
    for e in entries:
        by_norm.setdefault(norm(clean_name(e["n"])), e)

    def resolve(key):
        key = norm(key)
        if key in by_norm:
            return by_norm[key]
        hit = hit_cn = None
        for cn, e in by_norm.items():
            if cn.startswith(key + " ") and (hit is None or len(cn) < len(hit_cn)):
                hit, hit_cn = e, cn
        return hit

    # Load all shards; remember which (file, key) already owns each entity so
    # production_base can be merged into the SAME record, not a new one.
    shard_data = {}
    key_owner = {}
    for f in sorted(glob.glob(str(METADATA_DIR / "*.json"))):
        d = json.loads(Path(f).read_text("utf-8"))
        shard_data[f] = d
        for k in d:
            if k.startswith("_"):
                continue
            e = resolve(k)
            if e:
                key_owner[e["eid"]] = (f, k)

    rows = parse_input(args.input)
    print(f"input rows: {len(rows)}")

    misses = []
    companies_patch = {}   # eid -> (city, country)
    new_records = {}       # exact-match key -> minimal record
    prod_updates = 0

    for row in rows:
        e = resolve(row["name"])
        if not e:
            misses.append(row["name"])
            continue
        companies_patch[e["eid"]] = (row["city"], row["country"])
        if row["production_base"]:
            if e["eid"] in key_owner:
                f, k = key_owner[e["eid"]]
                shard_data[f][k]["production_base"] = row["production_base"]
            else:
                key = norm(clean_name(e["n"]))
                new_records[key] = {"type": e.get("et", "Corporate"),
                                     "production_base": row["production_base"]}
            prod_updates += 1

    print(f"resolved: {len(rows) - len(misses)}   unmatched: {len(misses)}")
    if misses:
        miss_path = Path(args.input).with_suffix(".misses.txt")
        miss_path.write_text("\n".join(misses), encoding="utf-8")
        print(f"  unmatched names written to {miss_path} for review")
        for m in misses[:20]:
            print("  MISS:", m)
        if len(misses) > 20:
            print(f"  ... and {len(misses) - 20} more")

    if args.dry_run:
        print("(dry run -- no files written)")
        return

    # --- patch data/companies.txt (preserve any field not being updated) ---
    id_to_eid = {e["i"]: e["eid"] for e in entries}
    entry_re = re.compile(r"^(\d+\.\s*)(.+?)\s*$")
    lines = COMPANIES.read_text(encoding="utf-8").splitlines()
    out, patched = [], 0
    for raw in lines:
        m = entry_re.match(raw)
        if m:
            prefix, text = m.groups()
            num = int(re.match(r"(\d+)", prefix).group(1))
            eid = id_to_eid.get(num)
            if eid in companies_patch:
                new_city, new_country = companies_patch[eid]
                base, *extras = [p.strip() for p in text.split("|")]
                kept, orig_country, orig_city = [], "", ""
                for x in extras:
                    xl = x.lower()
                    if xl.startswith("country="):
                        orig_country = x
                    elif xl.startswith("city="):
                        orig_city = x
                    else:
                        kept.append(x)
                final_country = f"country={new_country}" if new_country else orig_country
                final_city = f"city={new_city}" if new_city else orig_city
                pieces = [base] + kept + ([final_country] if final_country else []) \
                         + ([final_city] if final_city else [])
                out.append(prefix + " | ".join(pieces))
                patched += 1
                continue
        out.append(raw)
    COMPANIES.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"data/companies.txt: patched {patched} lines")

    # --- write back updated existing shards ---
    for f, d in shard_data.items():
        Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- new minimal records for entities with no prior metadata anywhere ---
    if new_records:
        doc = {"_doc": "Minimal production_base-only records for entities with no "
                       "other curated profile yet. Merge into a proper sector shard "
                       "if you later add a full profile for one of these. See "
                       "METADATA.md and data/LOCATION_PROMPT.md."}
        if NEW_SHARD.exists():
            doc = json.loads(NEW_SHARD.read_text("utf-8"))
        doc.update(new_records)
        NEW_SHARD.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{NEW_SHARD}: {len(new_records)} new minimal records")

    print(f"production_base set on {prod_updates} entities")
    print("Run `python3 build.py` to apply and check for [warn] lines.")


if __name__ == "__main__":
    main()
