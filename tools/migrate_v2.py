#!/usr/bin/env python3
"""Build data/companies.txt from data/_source_v2.txt (24-sector ecosystem map),
splitting the oversized cat 24 into four and re-appending the plant-level
gigafactory geo layer (with country tags) preserved from v1."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "_source_v2.txt"
GIGA = ROOT / "data" / "_gigafactories.txt"
OUT = ROOT / "data" / "companies.txt"

TITLES = {
    1: "Major Cell Manufacturers & Gigafactory Leaders",
    2: "Automotive OEMs — EV Focus",
    3: "Cell Materials — Cathode, Anode, Electrolyte & Separator",
    4: "BMS & Power Electronics",
    5: "Recycling & Second Life",
    6: "Research Institutes, Labs & University Centers",
    7: "Industry News, Analysis & Regional Portals",
    8: "Associations, Government & Standards",
    9: "Testing, Certification & Consulting",
    10: "Data, Software, AI & Cloud",
    11: "Mining & Raw Materials",
    12: "Equipment & Front-End Manufacturing",
    13: "Energy Storage Systems (ESS)",
    14: "Investment, Finance, ESG & IP",
    15: "Academic Journals & Trade Publications",
    16: "Components, Enclosures & Fastening",
    17: "Factory Software, MES & Metrology",
    18: "Thermal, Welding, Finishing & Utilities",
    19: "Logistics, Packaging & Supply-Chain Geography",
    20: "Insurance, Risk, Legal & Trade Policy",
    21: "Startups & Next-Gen Chemistry",
    22: "Charging, BaaS, Swapping & Cybersecurity",
    23: "Predictive Maintenance, Digital Twin, Robotics & Additive",
    # 24 splits by item index below
}
# cat24 split: (target_id, title, first_item_index_inclusive)
SPLIT24 = [
    (24, "Talent & Careers", 1),
    (25, "Education & Training", 42),
    (26, "Events, Media & Community", 71),
    (27, "Distribution & Sourcing Marketplaces", 142),
]

cat_re = re.compile(r"^##\s*(\d+)\.\s*(.+?)\s*$")
ent_re = re.compile(r"^(\d+)\.\s+(.+?)\s*$")

# parse source
groups = []  # list of (src_id, [names])
cur = None
for line in SRC.read_text(encoding="utf-8").splitlines():
    line = line.rstrip()
    if not line.strip() or line.lstrip().startswith("*"):
        continue
    m = cat_re.match(line)
    if m:
        cur = (int(m.group(1)), [])
        groups.append(cur)
        continue
    m = ent_re.match(line)
    if m and cur is not None:
        cur[1].append(m.group(2))

out = []
gid = 0  # global entry number
def emit_cat(cid, title):
    out.append(f"\n## {cid} | {title}")
def emit(name):
    global gid
    gid += 1
    out.append(f"{gid}. {name}")

for src_id, names in groups:
    if src_id != 24:
        emit_cat(src_id, TITLES[src_id])
        for n in names:
            emit(n)
    else:
        # split by 1-based item index
        bounds = SPLIT24 + [(None, None, 10**9)]
        for (tid, title, start), (_, _, nxt) in zip(SPLIT24, bounds[1:]):
            emit_cat(tid, title)
            for i, n in enumerate(names, 1):
                if start <= i < nxt:
                    emit(n)

# append gigafactory geo layer from v1 backup (categories 147/148/149)
giga_titles = {
    147: (28, "Gigafactories & Cell Plants — North America"),
    148: (29, "Gigafactories & Cell Plants — Europe"),
    149: (30, "Gigafactories & Cell Plants — Asia-Pacific"),
}
gcat_re = re.compile(r"^##\s*(\d+)\s*\|\s*(.+?)\s*$")
cur_new = None
for line in GIGA.read_text(encoding="utf-8").splitlines():
    line = line.rstrip()
    m = gcat_re.match(line)
    if m and int(m.group(1)) in giga_titles:
        tid, title = giga_titles[int(m.group(1))]
        emit_cat(tid, title); cur_new = True; continue
    if m:  # some other v1 category -> stop copying
        cur_new = False; continue
    m = re.match(r"^(\d+)\.\s+(.+?)\s*$", line)
    if m and cur_new:
        emit(m.group(2))  # keeps "| country=..." intact

OUT.write_text("\n".join(out).lstrip() + "\n", encoding="utf-8")
print(f"[ok] wrote {OUT} — {gid} entries, {sum(1 for l in out if l.startswith('## '))} categories")
