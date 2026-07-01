#!/usr/bin/env python3
"""
The Lithium Index — build script.

Parses data/companies.txt into structured JSON, assigns each of the 146
categories to one of 20 mega-sectors, and renders a single self-contained
HTML homepage (index.html) with no external runtime dependencies.

Usage:  python3 build.py
"""

import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "companies.txt"
OUT_HTML = ROOT / "index.html"
OUT_EMBED = ROOT / "blogger-embed.html"
OUT_PAGE = ROOT / "blogger-page.html"
OUT_JSON = ROOT / "data" / "directory.json"

# ---------------------------------------------------------------------------
# Mega-sector taxonomy: maps each category id (1-146) to a top-level sector.
# Any category id not listed falls back to "Other".
# ---------------------------------------------------------------------------
MEGA_SECTORS = {
    "Cell Manufacturing & OEMs": [1, 2, 33, 103, 104],
    "Materials & Chemicals": [3, 17, 55, 56, 57, 58, 85, 86],
    "Mining & Raw Materials": [11, 54],
    "BMS & Power Electronics": [4],
    "Recycling & Circular Economy": [5, 34, 59, 80, 132, 133],
    "Energy Storage & Charging": [13, 44, 45, 46],
    "Manufacturing Equipment": [12, 40, 41, 87, 89, 90, 91, 92, 93, 94, 95,
                                97, 98, 99, 100, 101, 102],
    "Process & Facility Systems": [32, 38, 39, 88, 96, 123, 124, 125],
    "Software, Data & Simulation": [10, 18, 35, 47, 48, 49, 70, 73, 74, 82,
                                    83, 84, 135],
    "Testing, Certification & Quality": [9, 27, 63, 68, 78, 105, 110, 111,
                                         112, 113],
    "Logistics & Supply Chain": [26, 37, 62, 76, 79, 106, 107, 108, 109,
                                 114, 140, 141],
    "Thermal & Safety": [19, 36],
    "Research & Academia": [6, 16, 52, 77],
    "Education, Training & Workforce": [22, 30, 50, 67, 117, 118, 121, 122],
    "Media, Community & Events": [7, 14, 20, 21, 31, 51, 71, 75, 81, 119, 120],
    "Finance & Investment": [15, 24, 60, 72, 126, 127],
    "Insurance & Risk": [25, 61, 128, 129],
    "Consulting & Professional Services": [28, 29, 43, 64, 115, 116, 130,
                                           131, 134, 136, 144, 145, 146],
    "Legal, IP & Policy": [23, 42, 65, 137, 138, 139, 142, 143],
    "Industry Bodies & Standards": [8, 53, 66, 69],
}

# ---------------------------------------------------------------------------
# Each mega-sector implies a coarse "entry type" used by the Type filter.
# ---------------------------------------------------------------------------
SECTOR_TYPE = {
    "Cell Manufacturing & OEMs": "Manufacturer / OEM",
    "Materials & Chemicals": "Materials",
    "Mining & Raw Materials": "Mining",
    "BMS & Power Electronics": "Components",
    "Recycling & Circular Economy": "Recycling",
    "Energy Storage & Charging": "ESS / Charging",
    "Manufacturing Equipment": "Equipment",
    "Process & Facility Systems": "Equipment",
    "Software, Data & Simulation": "Software",
    "Testing, Certification & Quality": "Testing / Certification",
    "Logistics & Supply Chain": "Logistics",
    "Thermal & Safety": "Equipment",
    "Research & Academia": "Research",
    "Education, Training & Workforce": "Education / Talent",
    "Media, Community & Events": "Media / Events",
    "Finance & Investment": "Finance",
    "Insurance & Risk": "Insurance",
    "Consulting & Professional Services": "Consulting",
    "Legal, IP & Policy": "Legal / Policy",
    "Industry Bodies & Standards": "Association / Standards",
}

# ---------------------------------------------------------------------------
# One accent color per mega-sector (assigned in MEGA_SECTORS order). Modern,
# saturated-but-professional palette; used on the sidebar, cards and pills to
# color-code the taxonomy.
# ---------------------------------------------------------------------------
SECTOR_COLORS = [
    "#2563eb", "#7c3aed", "#b45309", "#0891b2", "#16a34a",
    "#ea580c", "#4f46e5", "#0d9488", "#db2777", "#ca8a04",
    "#0284c7", "#dc2626", "#9333ea", "#059669", "#e11d48",
    "#15803d", "#a16207", "#1d4ed8", "#6d28d9", "#475569",
]

# ---------------------------------------------------------------------------
# Technology / chemistry tags, detected from the entry name + category text.
# (tag, [keywords]) — first keyword match adds the tag; an entry may carry
# several tags. Purely deterministic, no fabricated data.
# ---------------------------------------------------------------------------
TECH_RULES = [
    ("Solid-State", ["solid-state", "solid state", "solid electrolyte"]),
    ("LFP", ["lfp", "lithium iron", "iron phosphate"]),
    ("NMC / NCA", ["nmc", "ncm", "nca", "811", "622", "532"]),
    ("Sodium-ion", ["sodium-ion", "sodium ion", "sodium-metal", "na-ion"]),
    ("Silicon Anode", ["silicon"]),
    ("Lithium-Metal", ["lithium metal", "li-metal", "lithium-metal", "lithium-air", "lithium-water"]),
    ("Graphene", ["graphene"]),
    ("Supercapacitor", ["supercapacitor", "ultracapacitor"]),
    ("Cathode", ["cathode"]),
    ("Anode / Graphite", ["anode", "graphite"]),
    ("Electrolyte", ["electrolyte"]),
    ("Separator", ["separator"]),
    ("Alt. Chemistry", ["iron-air", "iron flow", "iron salt", "zinc-air", "zinc8",
                        "metal-hydrogen", "liquid metal", "magnesium", "flow battery",
                        "niobium"]),
]

# ---------------------------------------------------------------------------
# Curated verified official domains for high-confidence, unambiguous brands.
# Keys are cleaned, lowercased base names; an entry matches when its cleaned
# name equals a key or begins with "<key> ". Everything else falls back to a
# web search. Extend freely — or add "Name | https://url" lines in the data.
# ---------------------------------------------------------------------------
KNOWN_URLS = {
    "catl": "https://www.catl.com", "byd": "https://www.byd.com",
    "lg energy solution": "https://www.lgensol.com", "panasonic": "https://www.panasonic.com",
    "samsung sdi": "https://www.samsungsdi.com", "sk on": "https://www.sk-on.com",
    "tesla": "https://www.tesla.com", "northvolt": "https://northvolt.com",
    "eve energy": "https://www.evebattery.com", "gotion": "https://www.gotion.com.cn",
    "microvast": "https://microvast.com", "quantumscape": "https://www.quantumscape.com",
    "solid power": "https://www.solidpowerbattery.com", "sila": "https://www.silanano.com",
    "freyr": "https://www.freyrbattery.com", "enovix": "https://www.enovix.com",
    "rivian": "https://rivian.com", "lucid motors": "https://www.lucidmotors.com",
    "nio": "https://www.nio.com", "xpeng": "https://www.xpeng.com",
    "ford": "https://www.ford.com", "general motors": "https://www.gm.com",
    "volkswagen group": "https://www.volkswagen-group.com", "stellantis": "https://www.stellantis.com",
    "mercedes-benz": "https://www.mercedes-benz.com", "bmw": "https://www.bmwgroup.com",
    "hyundai": "https://www.hyundai.com", "toyota": "https://global.toyota",
    "honda": "https://global.honda", "polestar": "https://www.polestar.com",
    "vinfast": "https://vinfast.com",
    "umicore": "https://www.umicore.com", "basf": "https://www.basf.com",
    "johnson matthey": "https://matthey.com", "asahi kasei": "https://www.asahi-kasei.com",
    "toray industries": "https://www.toray.com", "solvay": "https://www.solvay.com",
    "arkema": "https://www.arkema.com", "3m": "https://www.3m.com", "henkel": "https://www.henkel.com",
    "texas instruments": "https://www.ti.com", "analog devices": "https://www.analog.com",
    "nxp": "https://www.nxp.com", "infineon": "https://www.infineon.com",
    "renesas": "https://www.renesas.com", "stmicroelectronics": "https://www.st.com",
    "bosch": "https://www.bosch.com",
    "li-cycle": "https://li-cycle.com", "redwood materials": "https://www.redwoodmaterials.com",
    "ascend elements": "https://ascendelements.com", "glencore": "https://www.glencore.com",
    "fluence": "https://www.fluenceenergy.com", "wärtsilä": "https://www.wartsila.com",
    "sungrow": "https://en.sungrowpower.com", "enersys": "https://www.enersys.com",
    "saft": "https://www.saftbatteries.com",
    "albemarle": "https://www.albemarle.com", "ganfeng lithium": "https://www.ganfenglithium.com",
    "rio tinto": "https://www.riotinto.com", "bhp": "https://www.bhp.com",
    "vale": "https://www.vale.com", "anglo american": "https://www.angloamerican.com",
    "siemens": "https://www.siemens.com", "abb": "https://global.abb",
    "rockwell automation": "https://www.rockwellautomation.com", "fanuc": "https://www.fanuc.co.jp",
    "kuka": "https://www.kuka.com", "yaskawa": "https://www.yaskawa.com",
    "dassault systèmes": "https://www.3ds.com", "ansys": "https://www.ansys.com",
    "comsol": "https://www.comsol.com", "ptc": "https://www.ptc.com",
    "mathworks": "https://www.mathworks.com", "altair": "https://altair.com",
    "sap": "https://www.sap.com", "oracle": "https://www.oracle.com",
    "trumpf": "https://www.trumpf.com", "coherent": "https://www.coherent.com",
    "ipg photonics": "https://www.ipgphotonics.com", "bühler": "https://www.buhlergroup.com",
    "manz": "https://www.manz.com",
    "chargepoint": "https://www.chargepoint.com", "evgo": "https://www.evgo.com",
    "electrify america": "https://www.electrifyamerica.com", "witricity": "https://witricity.com",
    "tüv süd": "https://www.tuvsud.com", "tüv rheinland": "https://www.tuv.com",
    "dnv": "https://www.dnv.com", "intertek": "https://www.intertek.com",
    "bureau veritas": "https://www.bureauveritas.com", "sgs": "https://www.sgs.com",
    "exponent": "https://www.exponent.com",
    "dhl": "https://www.dhl.com", "db schenker": "https://www.dbschenker.com",
    "kuehne + nagel": "https://www.kuehne-nagel.com",
    "mckinsey": "https://www.mckinsey.com", "boston consulting group": "https://www.bcg.com",
    "bain": "https://www.bain.com", "deloitte": "https://www.deloitte.com",
    "pwc": "https://www.pwc.com", "ey": "https://www.ey.com", "kpmg": "https://kpmg.com",
    "accenture": "https://www.accenture.com",
    "bloombergnef": "https://about.bnef.com", "idtechex": "https://www.idtechex.com",
    "benchmark mineral intelligence": "https://www.benchmarkminerals.com",
    "wood mackenzie": "https://www.woodmac.com",
    "argonne national laboratory": "https://www.anl.gov",
    "national renewable energy laboratory": "https://www.nrel.gov",
    "oak ridge national laboratory": "https://www.ornl.gov",
    "sandia national laboratories": "https://www.sandia.gov",
    "google patents": "https://patents.google.com",
    "the faraday institution": "https://www.faraday.ac.uk",
}


def clean_name(name):
    """Lowercased base name: drop parentheticals and trailing notes."""
    base = re.sub(r"\([^)]*\)", " ", name)
    base = re.split(r"\s[-/]\s", base)[0]  # cut " - note" / " / note"
    return re.sub(r"\s+", " ", base).strip().lower()


def match_url(name):
    """Longest-prefix match against KNOWN_URLS; '' if none."""
    cn = clean_name(name)
    best = ""
    for key, url in KNOWN_URLS.items():
        if cn == key or cn.startswith(key + " "):
            if len(key) > len(best):
                best, best_url = key, url
    return best and best_url or ""


def derive_tech(name, category):
    hay = (name + " " + category).lower()
    tags = []
    for tag, kws in TECH_RULES:
        if any(k in hay for k in kws):
            tags.append(tag)
    return tags


def build_category_lookup():
    """Return {category_id: mega_sector_name}."""
    lookup = {}
    for sector, ids in MEGA_SECTORS.items():
        for cid in ids:
            lookup[cid] = sector
    return lookup


def parse():
    cat_lookup = build_category_lookup()
    categories = []  # list of dicts {id,name,sector}
    entries = []     # list of dicts {id,name,category_id,category,sector}
    current = None

    cat_re = re.compile(r"^##\s*(\d+)\s*\|\s*(.+?)\s*$")
    entry_re = re.compile(r"^(\d+)\.\s*(.+?)\s*$")

    for raw in DATA.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = cat_re.match(line)
        if m:
            cid = int(m.group(1))
            name = m.group(2)
            sector = cat_lookup.get(cid, "Other")
            current = {"id": cid, "name": name, "sector": sector}
            categories.append(current)
            continue
        m = entry_re.match(line)
        if m and current is not None:
            text = m.group(2)
            # optional explicit URL:  "Name | https://example.com"
            url = ""
            if "|" in text:
                text, _, maybe = text.partition("|")
                text, maybe = text.strip(), maybe.strip()
                if maybe.startswith("http"):
                    url = maybe
            if not url:
                url = match_url(text)
            entries.append({
                "id": int(m.group(1)),
                "name": text,
                "cid": current["id"],
                "cat": current["name"],
                "sector": current["sector"],
                "url": url,
                "type": SECTOR_TYPE.get(current["sector"], "Other"),
                "tech": derive_tech(text, current["name"]),
            })
    return categories, entries


def main():
    categories, entries = parse()

    # sanity: warn about unmapped categories
    unmapped = sorted({c["id"] for c in categories if c["sector"] == "Other"})
    if unmapped:
        print(f"[warn] categories with no mega-sector: {unmapped}")

    # Stable sector ordering = insertion order of MEGA_SECTORS, then Other.
    sector_order = list(MEGA_SECTORS.keys()) + ["Other"]

    # Build the sector -> categories tree for the sidebar.
    tree = {s: [] for s in sector_order}
    counts_by_cat = {}
    for e in entries:
        counts_by_cat[e["cid"]] = counts_by_cat.get(e["cid"], 0) + 1
    for c in categories:
        tree[c["sector"]].append({
            "id": c["id"], "name": c["name"], "count": counts_by_cat.get(c["id"], 0)
        })
    tree = {s: cats for s, cats in tree.items() if cats}

    payload = {
        "entries": [
            {"i": e["id"], "n": e["name"], "c": e["cid"], "cn": e["cat"],
             "s": e["sector"], "u": e["url"], "t": e["type"], "tech": e["tech"]}
            for e in entries
        ],
        "tree": tree,
        "colors": {sec: SECTOR_COLORS[i % len(SECTOR_COLORS)]
                   for i, sec in enumerate(tree.keys())},
        "types": sorted({e["type"] for e in entries}),
        "techs": sorted({t for e in entries for t in e["tech"]}),
        "stats": {
            "entries": len(entries),
            "categories": len(categories),
            "sectors": len(tree),
            "withUrl": sum(1 for e in entries if e["url"]),
        },
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] wrote {OUT_JSON} ({len(entries)} entries, {len(categories)} categories, {len(tree)} sectors)")

    html = render(payload)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"[ok] wrote {OUT_HTML} ({OUT_HTML.stat().st_size/1024:.0f} KB)")

    embed = render_embed(payload)
    OUT_EMBED.write_text(embed, encoding="utf-8")
    print(f"[ok] wrote {OUT_EMBED} ({OUT_EMBED.stat().st_size/1024:.0f} KB)")

    page = render_blogger_page(payload)
    OUT_PAGE.write_text(page, encoding="utf-8")
    print(f"[ok] wrote {OUT_PAGE} ({OUT_PAGE.stat().st_size/1024:.0f} KB)")


def _fill(text, payload):
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    stats = payload["stats"]
    return text.replace("/*__DATA__*/", data_json) \
        .replace("__N_ENTRIES__", f'{stats["entries"]:,}') \
        .replace("__N_CATS__", str(stats["categories"])) \
        .replace("__N_SECTORS__", str(stats["sectors"]))


def render(payload):
    return _fill(TEMPLATE, payload)


def render_embed(payload):
    """Blogger-safe build: one scoped <div>, no <head>/<body>, @import fonts,
    container-query layout. Reuses the full template's markup + script so the
    two outputs never drift."""
    body_start = TEMPLATE.index("<body>") + len("<body>")
    script_start = TEMPLATE.index("<script>")
    markup = TEMPLATE[body_start:script_start].strip()
    script = TEMPLATE[script_start:TEMPLATE.index("</script>") + len("</script>")]
    embed = (
        "<!-- The Lithium Index — paste this whole block into a Blogger Page "
        "(HTML view) or an HTML/JavaScript gadget. Self-contained. -->\n"
        + STYLE_EMBED + "\n<div id=\"li-root\">\n" + markup
        + "\n</div>\n" + script + "\n"
    )
    return _fill(embed, payload)


def _search_url(name):
    clean = clean_name(name) or name
    from urllib.parse import quote
    return "https://www.google.com/search?q=" + quote(clean + " battery")


def render_blogger_page(payload):
    """No-JavaScript, no-form-element directory that survives Blogger's Page
    sanitizer. Pure <style> + <div>/<a> + native <details>/<summary>."""
    entries = payload["entries"]
    tree = payload["tree"]
    stats = payload["stats"]
    colors = payload["colors"]

    by_cat = {}
    for e in entries:
        by_cat.setdefault(e["c"], []).append(e)
    for lst in by_cat.values():
        lst.sort(key=lambda e: e["i"])

    def card(e):
        verified = bool(e["u"])
        href = e["u"] if verified else _search_url(e["n"])
        badge = '<span class="badge">✓ LINK</span>' if verified else ""
        tags = "".join(f'<span class="tag">{escape(t)}</span>' for t in e["tech"][:3])
        tags = f'<span class="tags">{tags}</span>' if tags else ""
        return (
            f'<a class="card{" v" if verified else ""}" '
            f'style="--sc:{colors.get(e["s"], "#0a0a0a")}" href="{escape(href)}" '
            f'target="_blank" rel="noopener">'
            f'<span class="idx">#{e["i"]}{badge}</span>'
            f'<span class="nm">{escape(e["n"])}</span>{tags}'
            f'<span class="go">↗ {"visit site" if verified else "web search"}</span></a>'
        )

    toc = "".join(
        f'<a href="#s{i}">{escape(sec)}</a>'
        for i, sec in enumerate(tree.keys(), 1)
    )

    sections = []
    for i, (sec, cats) in enumerate(tree.items(), 1):
        total = sum(c["count"] for c in cats)
        cat_blocks = []
        for c in cats:
            cards = "".join(card(e) for e in by_cat.get(c["id"], []))
            cat_blocks.append(
                f'<details class="cat"><summary><span>'
                f'<span class="tw">▸</span>{escape(c["name"])}</span>'
                f'<span class="scount">{c["count"]}</span></summary>'
                f'<div class="grid">{cards}</div></details>'
            )
        sections.append(
            f'<details class="sec" id="s{i}" style="--sc:{colors.get(sec, "#0a0a0a")}">'
            f'<summary><span class="snm">'
            f'<span class="tw">▸</span>{escape(sec)}</span>'
            f'<span class="scount">{total} entries · {len(cats)} categories</span>'
            f'</summary><div class="catwrap">{"".join(cat_blocks)}'
            f'<a class="top" href="#lx-top">↑ back to top</a></div></details>'
        )

    n_entries = f'{stats["entries"]:,}'
    return (
        "<!-- The Lithium Index — Blogger-PAGE-safe build (no JavaScript, no "
        "form elements). Paste this whole block into a Blogger Page/Post in "
        "HTML view. Browse by expanding sectors; use Ctrl/Cmd+F to find text. -->\n"
        + STYLE_PAGE + '\n<div id="lx"><a id="lx-top"></a>\n'
        f'<div class="head"><div class="brand"><span class="mark"></span>'
        f'<h1>The Lithium Index</h1></div>'
        f'<div class="sub">Li-ion Battery Industry Directory</div>'
        f'<div class="stat"><b>{n_entries}</b> entries · '
        f'<b>{stats["categories"]}</b> categories · '
        f'<b>{stats["sectors"]}</b> mega-sectors · '
        f'<b>{stats["withUrl"]}</b> verified links</div>'
        f'<div class="tip">Click a sector to expand · '
        f'press Ctrl/⌘+F to search the page</div></div>'
        f'<div class="toc">{toc}</div>'
        f'<div class="body">{"".join(sections)}</div>'
        f'<div class="foot">The Lithium Index · a ✓ marks a verified official '
        f'link, others open a web search · built as a static Blogger page</div>'
        "</div>\n"
    )


STYLE_PAGE = r"""<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Instrument+Serif:ital@0;1&display=swap');
#lx{
  --bg:#fafafa; --panel:#fff; --ink:#0a0a0a; --muted:#6b6b6b; --line:#e4e4e4;
  --ls:#0a0a0a; --blue:#1452ff; --orange:#ff5a1f; --grid:rgba(10,10,10,.035);
  container-type:inline-size;
  font-family:"JetBrains Mono",ui-monospace,monospace;
  color:var(--ink); font-size:13px; line-height:1.5; text-align:left;
  background:var(--bg);
  background-image:linear-gradient(var(--grid) 1px,transparent 1px),
                   linear-gradient(90deg,var(--grid) 1px,transparent 1px);
  background-size:48px 48px;
  border:1px solid var(--ls); overflow:hidden; box-sizing:border-box;
  position:relative; left:50%; transform:translateX(-50%);
  width:94vw; max-width:1500px; margin:20px 0;
  -webkit-font-smoothing:antialiased;
}
#lx *{box-sizing:border-box; margin:0; padding:0}
#lx a{color:inherit; text-decoration:none}
#lx summary::-webkit-details-marker{display:none}
#lx summary::marker{content:""}
#lx .head{padding:22px 20px; border-bottom:1px solid var(--ls); background:#fff; position:relative}
#lx .head::after{content:""; position:absolute; left:0; right:0; bottom:-1px; height:3px;
  background:linear-gradient(90deg,#2563eb,#7c3aed,#db2777,#ea580c,#f59e0b,#16a34a,#0891b2)}
#lx .brand{display:flex; align-items:baseline; gap:10px}
#lx .mark{width:11px; height:11px; background:var(--blue); box-shadow:3px 0 0 var(--orange)}
#lx h1{font-family:"Instrument Serif",Georgia,serif; font-style:italic; font-weight:400;
  font-size:30px; line-height:1}
#lx .sub{color:var(--muted); font-size:10px; letter-spacing:.18em; text-transform:uppercase; margin-top:8px}
#lx .stat{margin-top:12px; font-size:11px; color:var(--muted)}
#lx .stat b{color:var(--ink)}
#lx .tip{margin-top:8px; font-size:10px; color:var(--muted)}
#lx .toc{padding:14px 20px; border-bottom:1px solid var(--line); background:#fcfcfc;
  display:flex; flex-wrap:wrap; gap:6px}
#lx .toc a{font-size:10px; border:1px solid var(--ls); padding:4px 8px; background:#fff}
#lx .toc a:hover{background:var(--blue); color:#fff}
#lx .body{padding:16px 20px}
#lx details.sec{border:1px solid var(--ls); border-left:4px solid var(--sc,var(--ls)); background:#fff; margin-bottom:12px}
#lx details.sec>summary{list-style:none; cursor:pointer; padding:12px 14px;
  display:flex; justify-content:space-between; align-items:center; font-weight:500; font-size:14px}
#lx details.sec[open]>summary{background:var(--ink); color:#fff}
#lx .snm{display:flex; align-items:center}
#lx .tw{display:inline-block; font-size:10px; color:var(--muted); margin-right:9px; transition:transform .15s}
#lx details[open]>summary .tw{transform:rotate(90deg)}
#lx details.sec[open]>summary .tw{color:#fff}
#lx .scount{font-size:11px; color:var(--sc,var(--muted)); font-weight:700; white-space:nowrap; padding-left:12px}
#lx details.sec[open]>summary .scount{color:#bbb}
#lx .catwrap{padding:10px 12px}
#lx details.cat{border:1px solid var(--line); margin:8px 0; background:#fcfcfc}
#lx details.cat>summary{list-style:none; cursor:pointer; padding:9px 12px;
  display:flex; justify-content:space-between; align-items:center; font-size:12px; color:#222}
#lx details.cat[open]>summary{color:var(--blue); font-weight:700; border-bottom:1px solid var(--line)}
#lx details.cat>summary>span:first-child{display:flex; align-items:center}
#lx .grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:12px; padding:12px}
#lx .card{display:flex; flex-direction:column; gap:8px; border:1px solid var(--ls);
  border-top:3px solid var(--sc,var(--ls));
  background:#fff; padding:12px; min-height:112px; transition:box-shadow .08s}
#lx .card.v{box-shadow:inset 3px 0 0 var(--blue)}
#lx .card:hover{box-shadow:4px 4px 0 var(--ink)}
#lx .card.v:hover{box-shadow:4px 4px 0 var(--ink),inset 3px 0 0 var(--blue)}
#lx .idx{font-size:9px; color:var(--muted); letter-spacing:.1em;
  display:flex; justify-content:space-between; align-items:center}
#lx .badge{font-size:8px; letter-spacing:.12em; color:#fff; background:var(--blue); border:1px solid var(--blue); padding:1px 5px}
#lx .nm{font-family:"JetBrains Mono",ui-monospace,monospace; font-weight:700; font-size:14px;
  line-height:1.4; letter-spacing:-.2px; flex:1; overflow-wrap:anywhere; word-break:break-word}
#lx .tags{display:flex; flex-wrap:wrap; gap:4px}
#lx .tag{font-size:9px; color:#444; background:#f1f3ff; border:1px solid #d6ddff; padding:2px 6px}
#lx .go{font-size:10px; color:var(--muted); border-top:1px solid var(--line); padding-top:8px}
#lx .card:hover .go{color:var(--orange)}
#lx .top{display:block; text-align:right; font-size:10px; color:var(--blue); padding:8px 4px 2px}
#lx .foot{padding:20px; border-top:1px solid var(--ls); color:var(--muted); font-size:10px; background:#fff}
@container (max-width:440px){ #lx h1{font-size:24px} }
</style>"""


STYLE_EMBED = r"""<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Instrument+Serif:ital@0;1&display=swap');
#li-root{
  --bg:#fafafa; --panel:#ffffff; --ink:#0a0a0a; --muted:#6b6b6b;
  --line:#e4e4e4; --line-strong:#0a0a0a; --blue:#1452ff; --orange:#ff5a1f;
  --grid:rgba(10,10,10,.035); --cell:48px;
  container-type:inline-size;
  font-family:"JetBrains Mono",ui-monospace,monospace;
  color:var(--ink); font-size:13px; line-height:1.5; text-align:left;
  background:var(--bg);
  background-image:linear-gradient(var(--grid) 1px,transparent 1px),
                   linear-gradient(90deg,var(--grid) 1px,transparent 1px);
  background-size:var(--cell) var(--cell);
  border:1px solid var(--line-strong);
  box-sizing:border-box; overflow:hidden;
  /* Break out of the theme's (often narrow) content column and use the
     viewport width, capped, so the directory actually widens on big screens.
     Assumes a centered content column (the Blogger norm). */
  position:relative; left:50%; transform:translateX(-50%);
  width:94vw; max-width:1500px; margin:20px 0;
  -webkit-font-smoothing:antialiased;
}
#li-root *{box-sizing:border-box; margin:0; padding:0}
#li-root a{color:inherit;text-decoration:none}
#li-root button,#li-root input,#li-root select{font-family:inherit}
#li-root .menu-toggle{display:none !important}
#li-root h1{font-size:26px;font-weight:400}

#li-root header{display:block;position:relative;background:#fff;border-bottom:1px solid var(--line-strong)}
#li-root header::after{content:"";position:absolute;left:0;right:0;bottom:-1px;height:3px;
  background:linear-gradient(90deg,#2563eb,#7c3aed,#db2777,#ea580c,#f59e0b,#16a34a,#0891b2)}
#li-root .bar{padding:14px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
#li-root .brand{display:flex;align-items:baseline;gap:10px;white-space:nowrap}
#li-root .brand .mark{width:11px;height:11px;background:var(--blue);
  box-shadow:3px 0 0 var(--orange);transform:translateY(1px)}
#li-root .brand h1{font-family:"Instrument Serif",Georgia,serif;font-style:italic;
  font-weight:400;font-size:25px;letter-spacing:.2px;line-height:1}
#li-root .brand small{color:var(--muted);font-size:10px;letter-spacing:.18em;text-transform:uppercase}
#li-root .search{flex:1;min-width:200px;position:relative}
#li-root .search input{width:100%;font-size:13px;color:var(--ink);background:var(--panel);
  border:1px solid var(--line-strong);padding:11px 38px 11px 14px;outline:none}
#li-root .search input:focus{box-shadow:3px 3px 0 var(--blue)}
#li-root .search .kbd{position:absolute;right:10px;top:50%;transform:translateY(-50%);
  font-size:10px;color:var(--muted);border:1px solid var(--line);padding:1px 5px}
#li-root .stats{display:flex;gap:16px;white-space:nowrap}
#li-root .stats div{display:flex;flex-direction:column;line-height:1.1}
#li-root .stats b{font-size:16px}
#li-root .stats span{font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}

#li-root .wrap{display:block;padding:16px}
#li-root aside{border:1px solid var(--line-strong);background:var(--panel);
  margin-bottom:16px;max-height:none;overflow:visible}
#li-root .aside-h{padding:12px 14px;border-bottom:1px solid var(--line);
  font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);
  display:flex;justify-content:space-between;align-items:center}
#li-root .aside-h button{font-size:10px;background:none;border:none;color:var(--blue);
  cursor:pointer;letter-spacing:.1em}
#li-root .sector{border-bottom:1px solid var(--line);border-left:4px solid var(--sc,transparent)}
#li-root .sector>.row{display:flex;align-items:center;justify-content:space-between;
  padding:9px 12px;cursor:pointer;user-select:none}
#li-root .sector>.row:hover{background:#f3f3f3}
#li-root .sector>.row.on{background:var(--ink);color:#fff}
#li-root .sector .nm{font-weight:500;font-size:12px;display:flex;align-items:flex-start;gap:8px;min-width:0}
#li-root .sector .tw{font-size:9px;color:var(--muted);transition:transform .15s;flex:0 0 auto;margin-top:3px}
#li-root .sector>.row.on .tw{color:#bbb}
#li-root .sector .ct{font-size:10px;color:var(--sc,var(--muted));font-weight:700;white-space:nowrap;flex:0 0 auto;padding-left:10px}
#li-root .sector>.row.on .ct{color:#bbb}
#li-root .cats{display:none;background:#fcfcfc;border-top:1px solid var(--line)}
#li-root .sector.open .cats{display:block}
#li-root .sector.open .tw{transform:rotate(90deg)}
#li-root .cat{display:flex;justify-content:space-between;padding:7px 14px 7px 32px;
  cursor:pointer;font-size:11px;color:#333}
#li-root .cat:hover{background:#f0f0f0}
#li-root .cat.on{color:var(--blue);font-weight:700}
#li-root .cat .ct{color:var(--muted);font-weight:400}

#li-root main{min-width:0}
#li-root .toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px}
#li-root .pills{display:flex;gap:6px;flex-wrap:wrap}
#li-root .pill{font-size:11px;background:var(--panel);border:1px solid var(--line-strong);
  border-left:3px solid var(--sc,var(--line-strong));padding:6px 11px;cursor:pointer;white-space:nowrap}
#li-root .pill[data-pill="__all"]{border-left-width:1px}
#li-root .pill:hover{background:#f0f0f0}
#li-root .pill.on{background:var(--sc,var(--blue));border-color:var(--sc,var(--blue));color:#fff}
#li-root .spacer{flex:1}
#li-root .sort{font-size:11px;background:var(--panel);color:var(--ink);
  border:1px solid var(--line-strong);padding:6px 10px;cursor:pointer}
#li-root select.sort{appearance:none;-webkit-appearance:none;padding-right:22px;
  background-image:linear-gradient(45deg,transparent 50%,var(--ink) 50%),
                   linear-gradient(135deg,var(--ink) 50%,transparent 50%);
  background-position:calc(100% - 12px) 11px,calc(100% - 8px) 11px;
  background-size:4px 4px,4px 4px;background-repeat:no-repeat}
#li-root .chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}
#li-root .chip{display:inline-flex;align-items:center;gap:7px;font-size:11px;
  background:#fff;border:1px solid var(--line-strong);padding:5px 8px}
#li-root .chip b{font-weight:500}
#li-root .chip .x{cursor:pointer;color:var(--orange);font-weight:700}
#li-root .resultline{font-size:11px;color:var(--muted);margin-bottom:10px;letter-spacing:.04em}
#li-root .resultline b{color:var(--ink)}

#li-root .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}
#li-root .card{background:var(--panel);border:1px solid var(--line-strong);padding:15px 15px 13px;
  display:flex;flex-direction:column;gap:9px;min-height:124px;
  transition:transform .08s, box-shadow .08s;position:relative;overflow:hidden}
#li-root .card:hover{transform:translate(-2px,-2px);box-shadow:4px 4px 0 var(--ink)}
#li-root .card .nm{font-family:"JetBrains Mono",ui-monospace,monospace;font-weight:700;
  font-size:14px;line-height:1.4;letter-spacing:-.2px;flex:1;
  overflow-wrap:anywhere;word-break:break-word}
#li-root .card .meta{display:flex;flex-direction:column;gap:5px}
#li-root .card .cat{font-size:10px;color:var(--blue);letter-spacing:.02em;cursor:pointer;
  overflow-wrap:anywhere;line-height:1.35}
#li-root .card .cat:hover{text-decoration:underline}
#li-root .card{border-top:3px solid var(--sc,var(--ink))}
#li-root .card .sec{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--sc,var(--muted));
  display:flex;align-items:center;gap:5px}
#li-root .card .dot{width:7px;height:7px;border-radius:50%;background:var(--sc,var(--muted));flex:0 0 auto}
#li-root .card .go{font-size:10px;color:var(--muted);display:flex;align-items:center;
  gap:6px;border-top:1px solid var(--line);padding-top:9px;margin-top:2px}
#li-root .card:hover .go{color:var(--orange)}
#li-root .card.verified{box-shadow:inset 3px 0 0 var(--blue)}
#li-root .card.verified:hover{box-shadow:4px 4px 0 var(--ink),inset 3px 0 0 var(--blue)}
#li-root .card .idx{font-size:9px;color:var(--muted);letter-spacing:.1em;
  display:flex;align-items:center;justify-content:space-between}
#li-root .badge{font-size:8px;letter-spacing:.12em;color:#fff;background:var(--blue);
  border:1px solid var(--blue);padding:1px 5px}
#li-root .tags{display:flex;flex-wrap:wrap;gap:4px}
#li-root .tag{font-size:9px;letter-spacing:.04em;color:#444;background:#f1f3ff;
  border:1px solid #d6ddff;padding:2px 6px}
#li-root mark{background:linear-gradient(transparent 55%, #ffe08a 55%);color:inherit;padding:0}

#li-root .empty{padding:60px 20px;text-align:center;color:var(--muted);
  border:1px dashed var(--line-strong);background:var(--panel)}
#li-root .empty b{display:block;font-size:18px;color:var(--ink);margin-bottom:6px}

#li-root .pager{display:flex;align-items:center;justify-content:center;gap:6px;
  margin:26px 0 8px;flex-wrap:wrap}
#li-root .pager button{font-size:11px;background:var(--panel);border:1px solid var(--line-strong);
  padding:7px 12px;cursor:pointer;min-width:38px}
#li-root .pager button:hover:not(:disabled){background:#f0f0f0}
#li-root .pager button.on{background:var(--ink);color:#fff}
#li-root .pager button:disabled{opacity:.35;cursor:default}
#li-root .pager .gap{color:var(--muted);padding:0 2px}

#li-root footer{padding:22px 16px;border-top:1px solid var(--line-strong);
  color:var(--muted);font-size:10px;display:flex;justify-content:space-between;
  gap:16px;flex-wrap:wrap;background:#fff}
#li-root footer a{color:var(--blue)}

/* Layout adapts to the WIDGET width (container query), not the browser
   window — so it looks right inside a narrow Blogger content column. */
@container (min-width:680px){
  #li-root .wrap{display:grid;grid-template-columns:248px 1fr;gap:18px;align-items:start;padding:18px}
  #li-root aside{position:sticky;top:8px;max-height:80vh;overflow:auto;margin-bottom:0}
}
@container (max-width:679px){
  #li-root .pills{display:none}
  #li-root .toolbar{justify-content:flex-start}
}
@container (max-width:420px){
  #li-root .brand h1{font-size:21px}
  #li-root .stats{display:none}
}
</style>"""


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Lithium Index — Li-ion Battery Industry Directory</title>
<meta name="description" content="A futuristic-minimalist directory of __N_ENTRIES__ lithium-ion battery industry entries across __N_CATS__ categories and __N_SECTORS__ mega-sectors. Search, filter and drill down the entire Li-ion value chain.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#fafafa; --panel:#ffffff; --ink:#0a0a0a; --muted:#6b6b6b;
  --line:#e4e4e4; --line-strong:#0a0a0a;
  --blue:#1452ff; --orange:#ff5a1f;
  --grid:rgba(10,10,10,.03); --cell:48px;
  --maxw:1560px;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:"JetBrains Mono",ui-monospace,monospace;
  background:var(--bg); color:var(--ink); font-size:13px; line-height:1.5;
  background-image:linear-gradient(var(--grid) 1px,transparent 1px),
                   linear-gradient(90deg,var(--grid) 1px,transparent 1px);
  background-size:var(--cell) var(--cell);
  -webkit-font-smoothing:antialiased;
}
a{color:inherit;text-decoration:none}
.serif{font-family:"Instrument Serif",Georgia,serif;font-style:italic;font-weight:400}

/* ---------- header ---------- */
header{
  position:sticky;top:0;z-index:50;background:rgba(250,250,250,.86);
  backdrop-filter:blur(10px);border-bottom:1px solid var(--line-strong);
}
header::after{content:"";position:absolute;left:0;right:0;bottom:-1px;height:3px;
  background:linear-gradient(90deg,#2563eb,#7c3aed,#db2777,#ea580c,#f59e0b,#16a34a,#0891b2)}
.bar{max-width:var(--maxw);margin:0 auto;padding:14px 20px;
  display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.brand{display:flex;align-items:baseline;gap:10px;white-space:nowrap}
.brand .mark{width:11px;height:11px;background:var(--blue);
  box-shadow:3px 0 0 var(--orange);transform:translateY(1px)}
.brand h1{font-family:"Instrument Serif",Georgia,serif;font-style:italic;
  font-weight:400;font-size:26px;margin:0;letter-spacing:.2px}
.brand small{color:var(--muted);font-size:10px;letter-spacing:.18em;text-transform:uppercase}
.search{flex:1;min-width:220px;position:relative}
.search input{
  width:100%;font-family:inherit;font-size:13px;color:var(--ink);
  background:var(--panel);border:1px solid var(--line-strong);
  padding:11px 38px 11px 14px;outline:none}
.search input:focus{box-shadow:3px 3px 0 var(--blue)}
.search .kbd{position:absolute;right:10px;top:50%;transform:translateY(-50%);
  font-size:10px;color:var(--muted);border:1px solid var(--line);padding:1px 5px}
.stats{display:flex;gap:18px;white-space:nowrap}
.stats div{display:flex;flex-direction:column;line-height:1.1}
.stats b{font-size:16px}
.stats span{font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}

/* ---------- layout ---------- */
.wrap{max-width:var(--maxw);margin:0 auto;padding:20px;
  display:grid;grid-template-columns:264px 1fr;gap:20px;align-items:start}
aside{position:sticky;top:84px;border:1px solid var(--line-strong);
  background:var(--panel);max-height:calc(100vh - 104px);overflow:auto}
.aside-h{padding:12px 14px;border-bottom:1px solid var(--line);
  font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);
  display:flex;justify-content:space-between;align-items:center}
.aside-h button{font-family:inherit;font-size:10px;background:none;border:none;
  color:var(--blue);cursor:pointer;letter-spacing:.1em}
.sector{border-bottom:1px solid var(--line);border-left:4px solid var(--sc,transparent)}
.sector>.row{display:flex;align-items:center;justify-content:space-between;
  padding:9px 12px;cursor:pointer;user-select:none}
.sector>.row:hover{background:#f3f3f3}
.sector>.row.on{background:var(--ink);color:#fff}
.sector .nm{font-weight:500;font-size:12px;display:flex;align-items:flex-start;gap:8px;min-width:0}
.sector .tw{font-size:9px;color:var(--muted);transition:transform .15s;flex:0 0 auto;margin-top:3px}
.sector>.row.on .tw{color:#bbb}
.sector .ct{font-size:10px;color:var(--sc,var(--muted));font-weight:700;white-space:nowrap;flex:0 0 auto;padding-left:10px}
.sector>.row.on .ct{color:#bbb}
.cats{display:none;background:#fcfcfc;border-top:1px solid var(--line)}
.sector.open .cats{display:block}
.sector.open .tw{transform:rotate(90deg)}
.cat{display:flex;justify-content:space-between;padding:7px 14px 7px 32px;
  cursor:pointer;font-size:11px;color:#333}
.cat:hover{background:#f0f0f0}
.cat.on{color:var(--blue);font-weight:700}
.cat .ct{color:var(--muted);font-weight:400}

/* ---------- main ---------- */
main{min-width:0}
.toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.pills{display:flex;gap:6px;flex-wrap:wrap}
.pill{font-family:inherit;font-size:11px;background:var(--panel);
  border:1px solid var(--line-strong);border-left:3px solid var(--sc,var(--line-strong));
  padding:6px 11px;cursor:pointer;white-space:nowrap}
.pill[data-pill="__all"]{border-left-width:1px}
.pill:hover{background:#f0f0f0}
.pill.on{background:var(--sc,var(--blue));border-color:var(--sc,var(--blue));color:#fff}
.spacer{flex:1}
.sort{font-family:inherit;font-size:11px;background:var(--panel);color:var(--ink);
  border:1px solid var(--line-strong);padding:6px 10px;cursor:pointer}
select.sort{appearance:none;-webkit-appearance:none;padding-right:22px;
  background-image:linear-gradient(45deg,transparent 50%,var(--ink) 50%),
                   linear-gradient(135deg,var(--ink) 50%,transparent 50%);
  background-position:calc(100% - 12px) 11px,calc(100% - 8px) 11px;
  background-size:4px 4px,4px 4px;background-repeat:no-repeat}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px;min-height:0}
.chip{display:inline-flex;align-items:center;gap:7px;font-size:11px;
  background:#fff;border:1px solid var(--line-strong);padding:5px 8px}
.chip b{font-weight:500}
.chip .x{cursor:pointer;color:var(--orange);font-weight:700}
.resultline{font-size:11px;color:var(--muted);margin-bottom:10px;
  letter-spacing:.04em}
.resultline b{color:var(--ink)}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line-strong);padding:15px 15px 13px;
  display:flex;flex-direction:column;gap:9px;min-height:124px;
  transition:transform .08s, box-shadow .08s;position:relative;overflow:hidden}
.card:hover{transform:translate(-2px,-2px);box-shadow:4px 4px 0 var(--ink)}
.card .idx{font-size:9px;color:var(--muted);letter-spacing:.1em}
.card .nm{font-family:"JetBrains Mono",ui-monospace,monospace;font-weight:700;
  font-size:14px;line-height:1.4;letter-spacing:-.2px;flex:1;
  overflow-wrap:anywhere;word-break:break-word}
.card .meta{display:flex;flex-direction:column;gap:5px}
.card .cat{font-size:10px;color:var(--blue);letter-spacing:.02em;cursor:pointer;
  overflow-wrap:anywhere;line-height:1.35}
.card .cat:hover{text-decoration:underline}
.card{border-top:3px solid var(--sc,var(--ink))}
.card .sec{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--sc,var(--muted));
  display:flex;align-items:center;gap:5px}
.card .dot{width:7px;height:7px;border-radius:50%;background:var(--sc,var(--muted));flex:0 0 auto}
.card .go{font-size:10px;color:var(--muted);display:flex;align-items:center;
  gap:6px;border-top:1px solid var(--line);padding-top:9px;margin-top:2px}
.card:hover .go{color:var(--orange)}
.card.verified{box-shadow:inset 3px 0 0 var(--blue)}
.card.verified:hover{box-shadow:4px 4px 0 var(--ink),inset 3px 0 0 var(--blue)}
.card .idx{display:flex;align-items:center;justify-content:space-between}
.badge{font-size:8px;letter-spacing:.12em;color:#fff;background:var(--blue);
  border:1px solid var(--blue);padding:1px 5px}
.tags{display:flex;flex-wrap:wrap;gap:4px}
.tag{font-size:9px;letter-spacing:.04em;color:#444;background:#f1f3ff;
  border:1px solid #d6ddff;padding:2px 6px}
mark{background:linear-gradient(transparent 55%, #ffe08a 55%);color:inherit;padding:0}

.empty{padding:60px 20px;text-align:center;color:var(--muted);
  border:1px dashed var(--line-strong);background:var(--panel)}
.empty b{display:block;font-size:18px;color:var(--ink);margin-bottom:6px}

.pager{display:flex;align-items:center;justify-content:center;gap:6px;
  margin:26px 0 8px;flex-wrap:wrap}
.pager button{font-family:inherit;font-size:11px;background:var(--panel);
  border:1px solid var(--line-strong);padding:7px 12px;cursor:pointer;min-width:38px}
.pager button:hover:not(:disabled){background:#f0f0f0}
.pager button.on{background:var(--ink);color:#fff}
.pager button:disabled{opacity:.35;cursor:default}
.pager .gap{color:var(--muted);padding:0 2px}

footer{max-width:var(--maxw);margin:0 auto;padding:30px 20px 50px;
  border-top:1px solid var(--line);color:var(--muted);font-size:10px;
  display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
footer a{color:var(--blue)}

/* ---------- mobile ---------- */
.menu-toggle{display:none}
@media(max-width:900px){
  .wrap{grid-template-columns:1fr}
  aside{position:fixed;inset:0 auto 0 0;width:300px;max-height:100vh;z-index:60;
    transform:translateX(-105%);transition:transform .2s;box-shadow:6px 0 0 rgba(0,0,0,.06)}
  body.nav-open aside{transform:none}
  body.nav-open::after{content:"";position:fixed;inset:0;background:rgba(0,0,0,.3);z-index:55}
  .menu-toggle{display:inline-flex;font-family:inherit;font-size:11px;
    background:var(--panel);border:1px solid var(--line-strong);padding:6px 11px;cursor:pointer}
  .stats{display:none}
}
@media(max-width:560px){
  .brand h1{font-size:21px}
  .grid{grid-template-columns:1fr 1fr}
  .pills{display:none}
}
@media(max-width:420px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
  <div class="bar">
    <button class="menu-toggle" id="menuToggle">☰ Filters</button>
    <a class="brand" href="#" id="brandReset" title="Reset all filters">
      <span class="mark"></span>
      <span>
        <h1>The Lithium Index</h1><br>
        <small>Li-ion Battery Industry Directory</small>
      </span>
    </a>
    <div class="search">
      <input id="q" type="search" placeholder="Search companies, labs, equipment, services…" autocomplete="off" spellcheck="false">
      <span class="kbd">/</span>
    </div>
    <div class="stats">
      <div><b id="statShown">0</b><span>Showing</span></div>
      <div><b id="statCats">__N_CATS__</b><span>Categories</span></div>
      <div><b id="statSecs">__N_SECTORS__</b><span>Sectors</span></div>
    </div>
  </div>
</header>

<div class="wrap">
  <aside id="sidebar">
    <div class="aside-h">
      <span>Mega-Sectors</span>
      <button id="clearNav">Reset</button>
    </div>
    <div id="tree"></div>
  </aside>

  <main>
    <div class="toolbar">
      <div class="pills" id="pills"></div>
      <span class="spacer"></span>
      <select class="sort" id="typeSel" title="Filter by type"></select>
      <select class="sort" id="techSel" title="Filter by technology / chemistry"></select>
      <button class="sort" id="sortBtn">Sort: Relevance</button>
    </div>
    <div class="chips" id="chips"></div>
    <div class="resultline" id="resultLine"></div>
    <div class="grid" id="grid"></div>
    <div class="pager" id="pager"></div>
  </main>
</div>

<footer>
  <span>The Lithium Index · __N_ENTRIES__ entries · __N_CATS__ categories · __N_SECTORS__ mega-sectors</span>
  <span>Single-file build · ✓ marks a verified official link; others open a web search</span>
</footer>

<script>
const DB = /*__DATA__*/;
const PER_PAGE = 60;
const QUICK = ["Cell Manufacturing & OEMs","Materials & Chemicals","Mining & Raw Materials",
  "Recycling & Circular Economy","Manufacturing Equipment","Software, Data & Simulation"];

const state = {q:"", sector:null, cat:null, type:"", tech:"", sort:"rel", page:1};

const $ = s => document.querySelector(s);
const grid = $("#grid"), pager = $("#pager"), chips = $("#chips"),
      resultLine = $("#resultLine"), treeEl = $("#tree"), pillsEl = $("#pills");

// ---- build sidebar tree ----
function buildTree(){
  let html = "";
  for(const [sector,cats] of Object.entries(DB.tree)){
    const total = cats.reduce((a,c)=>a+c.count,0);
    html += `<div class="sector" data-sector="${esc(sector)}" style="--sc:${DB.colors[sector]||'#0a0a0a'}">
      <div class="row" data-act="sector">
        <span class="nm"><span class="tw">▶</span>${esc(sector)}</span>
        <span class="ct">${total}</span>
      </div>
      <div class="cats">
        ${cats.map(c=>`<div class="cat" data-cat="${c.id}">
            <span>${esc(c.name)}</span><span class="ct">${c.count}</span>
          </div>`).join("")}
      </div>
    </div>`;
  }
  treeEl.innerHTML = html;
}
function buildPills(){
  pillsEl.innerHTML = `<button class="pill" data-pill="__all">All sectors</button>` +
    QUICK.filter(s=>DB.tree[s]).map(s=>`<button class="pill" data-pill="${esc(s)}" style="--sc:${DB.colors[s]||'#0a0a0a'}">${esc(s)}</button>`).join("");
}
function buildSelects(){
  const typeSel=$("#typeSel"), techSel=$("#techSel");
  typeSel.innerHTML = `<option value="">All types</option>` +
    DB.types.map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join("");
  techSel.innerHTML = `<option value="">All technologies</option>` +
    DB.techs.map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join("");
}

function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));}

// ---- filtering ----
function filtered(){
  const q = state.q.trim().toLowerCase();
  let rows = DB.entries;
  if(state.cat){ rows = rows.filter(e=>e.c===state.cat); }
  else if(state.sector){ rows = rows.filter(e=>e.s===state.sector); }
  if(state.type){ rows = rows.filter(e=>e.t===state.type); }
  if(state.tech){ rows = rows.filter(e=>e.tech.indexOf(state.tech)>=0); }
  if(q){
    rows = rows.filter(e=>
      e.n.toLowerCase().includes(q) ||
      e.cn.toLowerCase().includes(q) ||
      e.s.toLowerCase().includes(q));
  }
  if(state.sort==="az"){
    rows = rows.slice().sort((a,b)=>a.n.localeCompare(b.n,undefined,{sensitivity:"base"}));
  }else if(state.sort==="za"){
    rows = rows.slice().sort((a,b)=>b.n.localeCompare(a.n,undefined,{sensitivity:"base"}));
  }
  return rows;
}

function hl(text, q){
  if(!q) return esc(text);
  const i = text.toLowerCase().indexOf(q);
  if(i<0) return esc(text);
  return esc(text.slice(0,i))+"<mark>"+esc(text.slice(i,i+q.length))+"</mark>"+esc(text.slice(i+q.length));
}

function searchUrl(name){
  const clean = name.replace(/\s*\([^)]*\)\s*/g," ").trim() || name;
  return "https://www.google.com/search?q="+encodeURIComponent(clean+" battery");
}

function render(){
  const rows = filtered();
  const q = state.q.trim().toLowerCase();
  const pages = Math.max(1, Math.ceil(rows.length/PER_PAGE));
  if(state.page>pages) state.page = pages;
  const start = (state.page-1)*PER_PAGE;
  const slice = rows.slice(start, start+PER_PAGE);

  $("#statShown").textContent = rows.length.toLocaleString();
  $("#statCats").textContent = new Set(rows.map(e=>e.c)).size;
  $("#statSecs").textContent = new Set(rows.map(e=>e.s)).size;
  resultLine.innerHTML = rows.length
    ? `Showing <b>${start+1}–${start+slice.length}</b> of <b>${rows.length.toLocaleString()}</b> entries`
    : "";

  if(!rows.length){
    grid.innerHTML = `<div class="empty" style="grid-column:1/-1">
      <b>No matches</b>Try a different term or clear the active filters.</div>`;
    pager.innerHTML=""; renderChips(); return;
  }

  grid.innerHTML = slice.map(e=>{
    const verified = !!e.u;
    const href = verified ? e.u : searchUrl(e.n);
    const tags = (e.tech||[]).slice(0,3)
      .map(t=>`<span class="tag">${esc(t)}</span>`).join("");
    return `
    <a class="card${verified?" verified":""}" style="--sc:${DB.colors[e.s]||'#0a0a0a'}" href="${href}" target="_blank" rel="noopener">
      <div class="idx">#${e.i}${verified?'<span class="badge">✓ LINK</span>':''}</div>
      <div class="nm">${hl(e.n,q)}</div>
      ${tags?`<div class="tags">${tags}</div>`:""}
      <div class="meta">
        <div class="cat" data-cat="${e.c}">${hl(e.cn,q)}</div>
        <div class="sec"><span class="dot"></span>${esc(e.s)}</div>
      </div>
      <div class="go">↗ ${verified?"visit site":"web search"}</div>
    </a>`;}).join("");

  renderPager(pages);
  renderChips();
  syncSidebar();
}

function renderChips(){
  const c = [];
  if(state.sector) c.push(`<span class="chip"><b>Sector:</b> ${esc(state.sector)} <span class="x" data-clear="sector">✕</span></span>`);
  if(state.cat){
    const name = (DB.entries.find(e=>e.c===state.cat)||{}).cn || ("#"+state.cat);
    c.push(`<span class="chip"><b>Category:</b> ${esc(name)} <span class="x" data-clear="cat">✕</span></span>`);
  }
  if(state.type) c.push(`<span class="chip"><b>Type:</b> ${esc(state.type)} <span class="x" data-clear="type">✕</span></span>`);
  if(state.tech) c.push(`<span class="chip"><b>Tech:</b> ${esc(state.tech)} <span class="x" data-clear="tech">✕</span></span>`);
  if(state.q.trim()) c.push(`<span class="chip"><b>Search:</b> "${esc(state.q.trim())}" <span class="x" data-clear="q">✕</span></span>`);
  chips.innerHTML = c.join("");
}

function renderPager(pages){
  if(pages<=1){pager.innerHTML="";return;}
  const p = state.page, out = [];
  const btn=(n,lbl,dis,on)=>`<button data-page="${n}" ${dis?"disabled":""} class="${on?"on":""}">${lbl||n}</button>`;
  out.push(btn(p-1,"‹ Prev",p<=1));
  const nums = new Set([1,2,pages-1,pages,p-1,p,p+1]);
  let last=0;
  for(let i=1;i<=pages;i++){
    if(!nums.has(i)) continue;
    if(i-last>1) out.push(`<span class="gap">…</span>`);
    out.push(btn(i,null,false,i===p));
    last=i;
  }
  out.push(btn(p+1,"Next ›",p>=pages));
  pager.innerHTML = out.join("");
}

function syncSidebar(){
  document.querySelectorAll(".sector").forEach(s=>{
    const on = s.dataset.sector===state.sector;
    s.querySelector(".row").classList.toggle("on",on);
    if(on) s.classList.add("open");
  });
  document.querySelectorAll(".cat").forEach(c=>{
    c.classList.toggle("on", Number(c.dataset.cat)===state.cat);
  });
  document.querySelectorAll(".pill").forEach(p=>{
    const v = p.dataset.pill;
    p.classList.toggle("on", v==="__all" ? (!state.sector&&!state.cat) : v===state.sector);
  });
}

// ---- events ----
function isStacked(){
  const w = document.querySelector(".wrap");
  return w && getComputedStyle(w).display !== "grid";
}
function flashResults(){
  // On narrow/stacked layouts the sidebar sits above the grid, so a filter
  // change happens off-screen. Scroll the results into view so it's obvious.
  if(!isStacked()) return;
  // Land on the result line (right above the cards), not the tall toolbar.
  const target = resultLine.textContent ? resultLine : (grid.firstElementChild ? grid : document.querySelector("main"));
  if(target) target.scrollIntoView({behavior:"smooth", block:"start"});
}
function scrollToSelectedSector(){
  // Bring the chosen mega-sector to the top so its sub-sectors are visible;
  // the user then taps a sub-sector to drop down to the entries.
  if(!isStacked()) return;
  const row = document.querySelector(".sector > .row.on");
  const el = row && row.closest(".sector");
  if(el) el.scrollIntoView({behavior:"smooth", block:"start"});
}
function setSector(s){ state.sector=s; state.cat=null; state.page=1; render(); if(s) scrollToSelectedSector(); }
function setCat(id){
  const e = DB.entries.find(e=>e.c===id);
  state.cat=id; state.sector=e?e.s:state.sector; state.page=1; render(); flashResults();
}

treeEl.addEventListener("click", ev=>{
  const sec = ev.target.closest(".sector");
  const catEl = ev.target.closest(".cat");
  if(catEl){ setCat(Number(catEl.dataset.cat)); closeNav(); return; }
  if(sec && ev.target.closest('[data-act="sector"]')){
    const name = sec.dataset.sector;
    sec.classList.toggle("open");
    setSector(state.sector===name?null:name);
  }
});
pillsEl.addEventListener("click", ev=>{
  const b = ev.target.closest(".pill"); if(!b) return;
  const v=b.dataset.pill;
  setSector(v==="__all"?null:(state.sector===v?null:v));
});
chips.addEventListener("click", ev=>{
  const x = ev.target.closest("[data-clear]"); if(!x) return;
  const k=x.dataset.clear;
  if(k==="sector") state.sector=null;
  if(k==="cat") state.cat=null;
  if(k==="type"){ state.type=""; $("#typeSel").value=""; }
  if(k==="tech"){ state.tech=""; $("#techSel").value=""; }
  if(k==="q"){ state.q=""; $("#q").value=""; }
  state.page=1; render();
});
grid.addEventListener("click", ev=>{
  const cat = ev.target.closest(".cat[data-cat]");
  if(cat){ ev.preventDefault(); setCat(Number(cat.dataset.cat)); }
});
pager.addEventListener("click", ev=>{
  const b=ev.target.closest("button[data-page]"); if(!b||b.disabled) return;
  state.page=Number(b.dataset.page); window.scrollTo({top:0,behavior:"smooth"}); render();
});

let t=null;
$("#q").addEventListener("input", e=>{
  clearTimeout(t);
  t=setTimeout(()=>{ state.q=e.target.value; state.page=1; render(); }, 140);
});
document.addEventListener("keydown", e=>{
  if(e.key==="/" && document.activeElement!==$("#q")){ e.preventDefault(); $("#q").focus(); }
  if(e.key==="Escape"){ $("#q").blur(); }
});

$("#typeSel").addEventListener("change", e=>{ state.type=e.target.value; state.page=1; render(); });
$("#techSel").addEventListener("change", e=>{ state.tech=e.target.value; state.page=1; render(); });

const SORTS=[["rel","Relevance"],["az","A → Z"],["za","Z → A"]];
$("#sortBtn").addEventListener("click", ()=>{
  const i=SORTS.findIndex(s=>s[0]===state.sort);
  const next=SORTS[(i+1)%SORTS.length];
  state.sort=next[0]; $("#sortBtn").textContent="Sort: "+next[1]; render();
});

$("#clearNav").addEventListener("click", resetAll);
$("#brandReset").addEventListener("click", e=>{e.preventDefault();resetAll();});
function resetAll(){ state.q="";state.sector=null;state.cat=null;state.type="";state.tech="";state.page=1;
  $("#q").value=""; $("#typeSel").value=""; $("#techSel").value="";
  document.querySelectorAll(".sector.open").forEach(s=>s.classList.remove("open")); render(); }

// mobile nav
const body=document.body;
$("#menuToggle").addEventListener("click",()=>body.classList.toggle("nav-open"));
function closeNav(){body.classList.remove("nav-open");}
document.addEventListener("click",e=>{
  if(body.classList.contains("nav-open") && !e.target.closest("aside") && !e.target.closest("#menuToggle"))
    closeNav();
});

buildTree(); buildPills(); buildSelects(); render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
