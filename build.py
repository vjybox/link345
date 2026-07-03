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
OUT_JSON = ROOT / "dist" / "directory.json"   # generated artifact (git-ignored)

# ---------------------------------------------------------------------------
# Mega-sector taxonomy: maps each category id (1-146) to a top-level sector.
# Any category id not listed falls back to "Other".
# ---------------------------------------------------------------------------
# 12 Loop-aligned mega-sectors over the 30 v2 categories (see data/companies.txt).
MEGA_SECTORS = {
    "Raw Materials & Mining": [11],
    "Materials & Components": [3, 16],
    "Cells & Chemistry": [1, 21, 28, 29, 30],
    "Manufacturing Equipment & Factory": [12, 17, 18, 23],
    "Power Electronics & BMS": [4],
    "Vehicles, ESS & Charging": [2, 13, 22],
    "Recycling & Circular Economy": [5],
    "Logistics & Supply Chain": [19],
    "Software, Data & Testing": [10, 9],
    "Capital, ESG & Risk": [14, 20],
    "Research, Standards & Media": [6, 8, 7, 15],
    "People, Education & Market": [24, 25, 26, 27],
}

# ---------------------------------------------------------------------------
# Each mega-sector implies a coarse "entry type" used by the Type filter.
# ---------------------------------------------------------------------------
SECTOR_TYPE = {
    "Raw Materials & Mining": "Mining",
    "Materials & Components": "Materials",
    "Cells & Chemistry": "Manufacturer / OEM",
    "Manufacturing Equipment & Factory": "Equipment",
    "Power Electronics & BMS": "Components",
    "Vehicles, ESS & Charging": "OEM / Deployment",
    "Recycling & Circular Economy": "Recycling",
    "Logistics & Supply Chain": "Logistics",
    "Software, Data & Testing": "Software / Testing",
    "Capital, ESG & Risk": "Finance / Risk",
    "Research, Standards & Media": "Research / Media",
    "People, Education & Market": "Talent / Market",
}

# ---------------------------------------------------------------------------
# One accent color per mega-sector (assigned in MEGA_SECTORS order). Modern,
# saturated-but-professional palette; used on the sidebar, cards and pills to
# color-code the taxonomy.
# ---------------------------------------------------------------------------
# Order + values validated with the dataviz palette checker (light & dark):
# lightness band, chroma floor, adjacent-pair CVD separation all PASS; the
# yellow/deep-blue contrast WARNs are relieved by direct labels on every mark.
SECTOR_COLORS = [
    "#2563eb", "#ea580c", "#16a34a", "#7c3aed", "#0891b2",
    "#dc2626", "#ca8a04", "#db2777", "#0d9488", "#9333ea",
    "#b45309", "#1d4ed8", "#15803d", "#e11d48", "#0284c7",
    "#a16207", "#6d28d9", "#059669", "#c2410c", "#4f46e5",
]
# Dark mode selects its own step where needed (yellow exceeds the dark band).
SECTOR_COLORS_DARK = list(SECTOR_COLORS)
SECTOR_COLORS_DARK[6] = "#d97706"


def palette_css():
    light = "".join(f"--c{i+1}:{c};" for i, c in enumerate(SECTOR_COLORS))
    dark = "".join(f"--c{i+1}:{c};" for i, c in enumerate(SECTOR_COLORS_DARK)
                   if c != SECTOR_COLORS[i])
    return light, dark

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
# Geography: country -> (lat, lon) centroid for the self-contained world map,
# country -> region for the Region facet, and a small HQ-country lookup for
# major brands so the facet has coverage beyond the location-tagged plants.
# ---------------------------------------------------------------------------
COUNTRY_CENTROIDS = {
    "China": (35, 105), "USA": (39, -98), "Germany": (51, 10),
    "South Korea": (36, 128), "Japan": (36, 138), "Sweden": (62, 15),
    "France": (46, 2), "UK": (54, -2), "Norway": (61, 8), "Hungary": (47, 19),
    "Poland": (52, 19), "Canada": (56, -106), "Spain": (40, -4),
    "Italy": (42, 12), "Netherlands": (52, 5), "Finland": (64, 26),
    "Australia": (-25, 133), "India": (22, 79), "Indonesia": (-2, 118),
    "Chile": (-30, -71), "Brazil": (-10, -55), "Mexico": (23, -102),
    "Czechia": (49, 15), "Slovakia": (48, 19), "Austria": (47, 14),
    "Switzerland": (47, 8), "Belgium": (50, 4), "Portugal": (39, -8),
    "Ireland": (53, -8), "Denmark": (56, 10), "Turkey": (39, 35),
    "Morocco": (32, -6), "Serbia": (44, 20), "Thailand": (15, 101),
    "Vietnam": (16, 106), "Taiwan": (24, 121), "Singapore": (1, 104),
    "Russia": (61, 100), "Argentina": (-34, -64), "South Africa": (-30, 25),
}

REGION_OF = {
    "China": "Asia-Pacific", "South Korea": "Asia-Pacific", "Japan": "Asia-Pacific",
    "India": "Asia-Pacific", "Indonesia": "Asia-Pacific", "Thailand": "Asia-Pacific",
    "Vietnam": "Asia-Pacific", "Taiwan": "Asia-Pacific", "Singapore": "Asia-Pacific",
    "Australia": "Asia-Pacific",
    "USA": "North America", "Canada": "North America", "Mexico": "North America",
    "Chile": "South America", "Brazil": "South America", "Argentina": "South America",
    "Morocco": "Africa", "South Africa": "Africa", "Turkey": "Middle East",
    "Germany": "Europe", "Sweden": "Europe", "France": "Europe", "UK": "Europe",
    "Norway": "Europe", "Hungary": "Europe", "Poland": "Europe", "Spain": "Europe",
    "Italy": "Europe", "Netherlands": "Europe", "Finland": "Europe", "Czechia": "Europe",
    "Slovakia": "Europe", "Austria": "Europe", "Switzerland": "Europe", "Belgium": "Europe",
    "Portugal": "Europe", "Ireland": "Europe", "Denmark": "Europe", "Serbia": "Europe",
    "Russia": "Europe",
}

# HQ country for major, unambiguous brands (cleaned-name prefix match, like URLs).
KNOWN_COUNTRY = {
    "catl": "China", "byd": "China", "eve energy": "China", "calb": "China",
    "gotion": "China", "svolt": "China", "sunwoda": "China", "farasis": "China",
    "ganfeng lithium": "China", "tianqi lithium": "China", "cmoc": "China",
    "zijin mining": "China", "lg energy solution": "South Korea", "lg chem": "South Korea",
    "samsung sdi": "South Korea", "sk on": "South Korea", "posco": "South Korea",
    "ecopro": "South Korea", "panasonic": "Japan", "toyota": "Japan", "honda": "Japan",
    "nissan": "Japan", "sumitomo metal mining": "Japan", "toray": "Japan",
    "asahi kasei": "Japan", "gs yuasa": "Japan", "tesla": "USA", "rivian": "USA",
    "lucid": "USA", "general motors": "USA", "ford": "USA", "redwood materials": "USA",
    "quantumscape": "USA", "solid power": "USA", "sila": "USA", "enovix": "USA",
    "form energy": "USA", "microvast": "USA", "albemarle": "USA", "amprius": "USA",
    "group14": "USA", "our next energy": "USA", "one": "USA", "kore power": "USA",
    "northvolt": "Sweden", "freyr": "Norway", "morrow": "Norway", "verkor": "France",
    "saft": "France", "acc": "France", "automotive cells": "France", "umicore": "Belgium",
    "solvay": "Belgium", "basf": "Germany", "volkswagen": "Germany", "bmw": "Germany",
    "mercedes-benz": "Germany", "bosch": "Germany", "customcells": "Germany",
    "prologium": "Taiwan", "vinfast": "Vietnam", "inobat": "Slovakia",
    "britishvolt": "UK", "agratas": "UK", "johnson matthey": "UK", "nyobolt": "UK",
    "amte power": "UK", "ola electric": "India", "reliance": "India", "amara raja": "India",
    "exide": "India", "rio tinto": "Australia", "bhp": "Australia", "pilbara minerals": "Australia",
    "syrah resources": "Australia", "sqm": "Chile", "vale": "Brazil", "eramet": "France",
    "glencore": "Switzerland", "sungrow": "China", "fluence": "USA",
    "xiaomi": "China", "leapmotor": "China", "gac": "China", "changan": "China",
    "great wall": "China", "chery": "China", "dongfeng": "China", "seres": "China",
    "saic": "China", "geely": "China", "nio": "China", "xpeng": "China", "li auto": "China",
    "calb": "China", "svolt": "China", "hithium": "China", "narada": "China",
    "kia": "South Korea", "hyundai": "South Korea", "audi": "Germany", "porsche": "Germany",
    "volvo cars": "Sweden", "renault": "France", "stellantis": "Netherlands",
    "tata motors": "India", "mahindra": "India", "amara raja": "India",
    "sigma lithium": "Brazil", "liontown": "Australia", "novonix": "Australia",
    "talga": "Australia", "syrah": "Australia", "wärtsilä": "Finland", "verkor": "France",
}

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


def match_country(name):
    """Longest-prefix match against KNOWN_COUNTRY; '' if none."""
    cn = clean_name(name)
    best = ""
    for key, country in KNOWN_COUNTRY.items():
        if cn == key or cn.startswith(key + " "):
            if len(key) > len(best):
                best, best_country = key, country
    return best and best_country or ""


# --- metadata (Phase 1): stable IDs + auto-derived base fields --------------
ENTITY_TYPE_BY_CAT = {
    6: "Research", 8: "Institution", 7: "Media", 15: "Media",
    28: "Facility", 29: "Facility", 30: "Facility",
}


def slugify(name):
    base = re.sub(r"\([^)]*\)", " ", name)
    base = re.split(r"\s[-–/|]\s", base)[0]
    base = re.sub(r"[^A-Za-z0-9]+", "-", base).strip("-").lower()
    return "-".join(base.split("-")[:4]) or "x"


def infer_status(name):
    n = name.lower()
    if re.search(r"\b1\d{3}-\d{4}\b", n):
        return "Defunct"
    if any(w in n for w in ("acquired by", "acquired", "now part of", "now ",
                            "acquiring")):
        return "Acquired"
    if "merger" in n or "formerly" in n:
        return "Active"
    return "Active"


def infer_one_liner(name):
    m = re.search(r"\(([^)]+)\)", name)
    if m:
        txt = m.group(1).strip()
        if len(txt) > 3 and not txt.lower().startswith(("nyse", "nasdaq",
                                                        "szse", "krx", "etr")):
            return txt
    parts = re.split(r"\s[-–]\s", name, 1)
    return parts[1].strip() if len(parts) > 1 else ""


# Plain-language tooltips for technology jargon (learner-friendly).
GLOSSARY = {
    "Solid-State": "Solid electrolyte instead of liquid — higher energy density and safety",
    "LFP": "Lithium Iron Phosphate (LiFePO4) — cobalt-free cathode; long life, lower cost",
    "NMC / NCA": "Nickel Manganese Cobalt / Nickel Cobalt Aluminium — high-energy cathode chemistries",
    "Sodium-ion": "Uses sodium instead of lithium — cheaper, abundant materials",
    "Silicon Anode": "Silicon replaces graphite in the anode for higher capacity",
    "Lithium-Metal": "Pure lithium-metal anode — next-generation energy density",
    "Graphene": "Carbon nanomaterial used for electrodes and conductivity",
    "Supercapacitor": "Stores charge electrostatically — very fast charge/discharge",
    "Cathode": "The positive electrode of a battery cell",
    "Anode / Graphite": "The negative electrode of a cell, typically graphite",
    "Electrolyte": "The medium that carries lithium ions between electrodes",
    "Separator": "Membrane keeping electrodes apart while letting ions pass",
    "Alt. Chemistry": "Beyond Li-ion: flow, zinc, iron-air and other chemistries",
}


# ---------------------------------------------------------------------------
# The Loop — linkplus.in circular-economy mapping. Core stages are arcs on the
# ring; "links" ride the connectors; enablers orbit (every other sector).
# ---------------------------------------------------------------------------
LIFECYCLE_STAGES = [
    ("Extract", ["Raw Materials & Mining"]),
    ("Refine", ["Materials & Components"]),
    ("Manufacture", ["Cells & Chemistry", "Manufacturing Equipment & Factory",
                     "Power Electronics & BMS"]),
    ("Deploy & Use", ["Vehicles, ESS & Charging"]),
    ("Recover ♻", ["Recycling & Circular Economy"]),
]
LINKS_SECTORS = ["Logistics & Supply Chain"]


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
            # optional pipe-separated fields:
            #   "Name | https://url | country=Germany | logo=https://logo.svg"
            url, country, logo = "", "", ""
            if "|" in text:
                parts = [p.strip() for p in text.split("|")]
                text = parts[0]
                for extra in parts[1:]:
                    if extra.startswith("http"):
                        url = extra
                    elif "=" in extra:
                        k, _, v = extra.partition("=")
                        k = k.strip().lower()
                        if k == "country":
                            country = v.strip()
                        elif k == "logo":
                            logo = v.strip()
            if not url:
                url = match_url(text)
            if not country:
                country = match_country(text)
            entries.append({
                "id": int(m.group(1)),
                "name": text,
                "cid": current["id"],
                "cat": current["name"],
                "sector": current["sector"],
                "url": url,
                "logo": logo,
                "type": SECTOR_TYPE.get(current["sector"], "Other"),
                "tech": derive_tech(text, current["name"]),
                "country": country,
                "region": REGION_OF.get(country, ""),
            })
    return categories, entries


# ---------------------------------------------------------------------------
# Per-entry content pages (static HTML + Blogger import XML).
# Generated by build.py from the same data — no API, no runtime cost.
# ---------------------------------------------------------------------------

# How to describe an entry in prose, by mega-sector (Corporate default).
SECTOR_NOUN = {
    "Raw Materials & Mining": "mining & raw-materials company",
    "Materials & Components": "battery-materials company",
    "Cells & Chemistry": "battery cell manufacturer",
    "Manufacturing Equipment & Factory": "battery-manufacturing equipment maker",
    "Power Electronics & BMS": "power-electronics & BMS company",
    "Vehicles, ESS & Charging": "vehicle, storage & charging company",
    "Recycling & Circular Economy": "battery recycler",
    "Logistics & Supply Chain": "logistics & supply-chain company",
    "Software, Data & Testing": "battery software & testing company",
    "Capital, ESG & Risk": "investment / risk & ESG organisation",
    "Research, Standards & Media": "research, standards & media organisation",
    "People, Education & Market": "battery-industry participant",
}

# Ordered (field -> label) used for the facts table; mirrors PROFILE_ROWS in JS.
PAGE_FACTS = [
    ("ownership", "Ownership"), ("founded", "Founded"), ("ticker", "Ticker"),
    ("product", "Core product / material"), ("chemistry", "Chemistry"),
    ("form_factor", "Form factor"), ("deployment", "Deployment"),
    ("target", "Target market"), ("key_ip", "Key IP"), ("extraction", "Extraction"),
    ("facility_type", "Facility type"), ("capacity", "Capacity"),
    ("hazmat", "Hazmat handling"), ("strategic_role", "Strategic role"),
    ("city", "Location"), ("institution_type", "Institution type"),
    ("funding_source", "Funding source"), ("notable_facility", "Facility"),
    ("title", "Role"), ("expertise", "Expertise"), ("esg", "ESG"),
    ("media_type", "Format"),
]


def _stage_of_sector(payload, sector):
    for st in payload["stages"]:
        if sector in st["sectors"]:
            return st["n"]
    return "Enablers"


def _entry_slug(e):
    """Unique, stable, URL-safe slug per entry (eid already encodes cid+name)."""
    return e["eid"].lower()


def _page_prose(e, payload, rels):
    """Deterministic, grammatical 'About' paragraph composed from the data.
    An optional curated `about` field (e.g. from a local LLM) overrides it."""
    m = e.get("m") or {}
    if m.get("about"):
        return m["about"]
    name = e["n"]
    et = e.get("et", "Corporate")
    country = e.get("co", "")
    sents = []

    # Lead sentence from the one-liner (always present; curated or inferred).
    if e.get("one"):
        sents.append(e["one"].rstrip(".") + ".")

    # Identity sentence, tailored to entity type.
    if et == "People":
        bits = []
        if m.get("title"):
            bits.append(m["title"])
        ident = f"{name} is " + ("an industry figure" if not bits else bits[0])
        sents.append(ident + ".")
        if m.get("expertise"):
            sents.append(f"Expertise: {m['expertise']}.")
    elif et in ("Facility",):
        noun = m.get("facility_type", "facility")
        s = f"{name} is a {noun.lower()}"
        if m.get("city"):
            s += f" in {m['city']}"
        elif country:
            s += f" in {country}"
        sents.append(s + ".")
        if m.get("strategic_role"):
            sents.append(m["strategic_role"].rstrip(".") + ".")
    elif et in ("Research", "Institution"):
        noun = m.get("institution_type", "research organisation")
        s = f"{name} is a {noun.lower()}"
        if country:
            s += f" based in {country}"
        sents.append(s + ".")
        if m.get("funding_source"):
            sents.append(f"Funded by {m['funding_source']}.")
    elif et == "Media":
        noun = m.get("media_type", "industry media outlet")
        sents.append(f"{name} is a {noun.lower()} covering the battery industry.")
    else:  # Corporate and everything else
        noun = SECTOR_NOUN.get(e["s"], "battery-industry company")
        own = (m.get("ownership", "") or "").lower()
        lead = f"{name} is a"
        if own in ("public", "private", "state-owned"):
            lead += f" {own}"
        s = f"{lead} {noun}"
        if country:
            s += f" based in {country}"
        if m.get("founded"):
            s += f", founded in {m['founded']}"
        sents.append(s + ".")
        prod = []
        if m.get("product"):
            prod.append(m["product"])
        detail = ""
        if m.get("chemistry"):
            detail += f" ({m['chemistry']}"
            detail += f", {m['form_factor']})" if m.get("form_factor") else ")"
        elif m.get("form_factor"):
            detail += f" ({m['form_factor']})"
        if prod:
            sents.append(f"Its core focus is {prod[0]}{detail}.")

    # Connections sentence from the graph (up to 4 outgoing edges).
    out = [r for r in (rels.get(e["eid"]) or []) if r["d"] == "out"][:4]
    if out:
        verbs = {
            "SUPPLIES_TO": "supplies", "SUPPLIES_EQUIPMENT_TO": "supplies equipment to",
            "EXPORTS_THROUGH": "exports through", "USES_SOFTWARE": "uses software from",
            "INVESTED_IN": "has invested in", "RECYCLES_FOR": "recycles for",
            "JV_WITH": "runs a joint venture with", "PARTNER_OF": "partners with",
            "FOUNDER_OF": "founded", "LEADS": "leads", "MEMBER_OF": "is a member of",
            "COVERS": "covers", "SUBSIDIARY_OF": "is a subsidiary of",
            "COMPETES_WITH": "competes with", "FORMER_EMPLOYER": "previously worked at",
        }
        by_verb = {}
        for r in out:
            by_verb.setdefault(verbs.get(r["r"], "is linked to"), []).append(r["n"])
        clauses = [f"{v} {_and_list(names)}" for v, names in by_verb.items()]
        sents.append(f"{name.split('(')[0].strip()} {'; '.join(clauses)}.")

    # Loop placement.
    stage = _stage_of_sector(payload, e["s"])
    sents.append(f"In the battery circular economy, it sits at the {stage} stage "
                 f"of the loop.")
    return " ".join(sents)


def _and_list(names):
    names = list(dict.fromkeys(names))
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def _page_facts_rows(e):
    m = e.get("m") or {}
    rows = []
    status = m.get("status") or e.get("stt")
    if status:
        rows.append(("Status", status))
    if e.get("co"):
        rows.append(("Country", e["co"]))
    if e.get("cn"):
        rows.append(("Category", e["cn"]))
    for k, label in PAGE_FACTS:
        v = m.get(k)
        if v not in (None, ""):
            rows.append((label, str(v)))
    if e.get("tech"):
        rows.append(("Tags", ", ".join(e["tech"])))
    return rows


def _research_links(e):
    from urllib.parse import quote_plus
    cn = clean_name(e["n"])
    links = []
    if e.get("u"):
        links.append(("Official site", e["u"]))
    links.append(("News", "https://www.google.com/search?tbm=nws&q=" + quote_plus(cn + " battery")))
    links.append(("LinkedIn", "https://www.google.com/search?q=" + quote_plus(cn + " site:linkedin.com/company")))
    links.append(("Patents", "https://patents.google.com/?q=" + quote_plus(cn)))
    return links


def _entry_content_html(e, payload, rels, by_eid, by_cat):
    """Inner content (no <head>): reused by both the static page and the XML."""
    color = payload["colors"].get(e["s"], "#0a0a0a")
    stage = _stage_of_sector(payload, e["s"])
    prose = _page_prose(e, payload, rels)

    facts = _page_facts_rows(e)
    facts_html = ""
    if facts:
        facts_html = ('<h2>Key facts</h2><table class="facts">'
                      + "".join(f'<tr><th>{escape(k)}</th><td>{escape(v)}</td></tr>'
                                for k, v in facts) + "</table>")

    conns = rels.get(e["eid"]) or []
    conn_html = ""
    if conns:
        labels = {"SUPPLIES_TO": "supplies", "SUPPLIES_EQUIPMENT_TO": "supplies equipment",
                  "EXPORTS_THROUGH": "exports through", "USES_SOFTWARE": "uses",
                  "INVESTED_IN": "invested in", "SUBSIDIARY_OF": "subsidiary of",
                  "PARTNER_OF": "partner", "JV_WITH": "joint venture",
                  "RECYCLES_FOR": "recycles for", "COMPETES_WITH": "competes with",
                  "FOUNDER_OF": "founder of", "FORMER_EMPLOYER": "formerly at",
                  "LEADS": "leads", "MEMBER_OF": "member of", "COVERS": "covers"}
        items = []
        for r in conns:
            lbl = labels.get(r["r"], r["r"].lower().replace("_", " "))
            arrow = "&rarr;" if r["d"] == "out" else "&larr;"
            tgt = by_eid.get(r["e"])
            nm = escape(r["n"])
            if tgt:
                nm = f'<a href="{_entry_slug(tgt)}.html">{nm}</a>'
            items.append(f'<li><span class="rel">{arrow} {escape(lbl)}</span> {nm}</li>')
        conn_html = f'<h2>Connections <span class="n">{len(conns)}</span></h2><ul class="conns">' + "".join(items) + "</ul>"

    related = [x for x in by_cat.get(e["c"], []) if x["eid"] != e["eid"]][:8]
    rel_html = ""
    if related:
        rel_html = ('<h2>Related in this category</h2><ul class="related">'
                    + "".join(f'<li><a href="{_entry_slug(x)}.html">{escape(x["n"])}</a></li>'
                              for x in related) + "</ul>")

    rlinks = _research_links(e)
    rlinks_html = ('<div class="links">'
                   + "".join(f'<a href="{escape(u)}" rel="noopener nofollow">{escape(t)} &#8599;</a>'
                             for t, u in rlinks) + "</div>")

    badges = (f'<span class="badge" style="--sc:{color}">{escape(e["s"])}</span>'
              f'<span class="badge loop">Loop: {escape(stage)}</span>')
    if e.get("co"):
        badges += f'<span class="badge">{escape(e["co"])}</span>'

    return (f'<div class="badges">{badges}</div>'
            f'<p class="lead">{escape(prose)}</p>'
            f'{facts_html}{conn_html}{rel_html}'
            f'<h2>Research</h2>{rlinks_html}')


PAGE_CSS = """*{box-sizing:border-box}
body{margin:0;font-family:Inter,system-ui,-apple-system,sans-serif;color:#111;background:#fafafa;line-height:1.55}
a{color:#1452ff;text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:820px;margin:0 auto;padding:24px 20px 64px}
header.site{border-bottom:1px solid #e5e5e5;background:#1b1c1e}
header.site .wrap{padding:12px 20px;display:flex;align-items:baseline;gap:10px}
.brand{font-family:"Instrument Serif",Georgia,serif;font-style:italic;font-size:22px;color:#fff}
.brand b{color:#d92d0a;font-style:normal}
.crumb{font-size:12px;color:#666;margin:14px 0 4px}
.crumb a{color:#666}
h1{font-family:"Instrument Serif",Georgia,serif;font-style:italic;font-weight:400;font-size:38px;margin:.1em 0 .2em}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 18px}
.badge{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:11px;padding:3px 8px;border:1px solid #ddd;border-radius:2px;color:#333}
.badge[style]{border-left:3px solid var(--sc)}
.badge.loop{background:#fff5f3;border-color:#f3c9bf;color:#b3260a}
.lead{font-size:17px;color:#222}
h2{font-size:14px;text-transform:uppercase;letter-spacing:.06em;color:#666;margin:28px 0 10px;font-family:"JetBrains Mono",ui-monospace,monospace}
h2 .n{color:#999}
table.facts{width:100%;border-collapse:collapse;font-size:14px}
table.facts th{text-align:left;width:200px;color:#666;font-weight:600;padding:7px 12px 7px 0;vertical-align:top;border-bottom:1px solid #eee}
table.facts td{padding:7px 0;border-bottom:1px solid #eee}
ul.conns,ul.related{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:6px}
ul.conns .rel{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:12px;color:#888;margin-right:6px}
ul.related{flex-direction:row;flex-wrap:wrap;gap:8px}
ul.related li{border:1px solid #e5e5e5;padding:5px 10px;border-radius:2px;font-size:13px}
.links{display:flex;flex-wrap:wrap;gap:8px}
.links a{border:1px solid #ddd;padding:6px 11px;border-radius:2px;font-size:13px}
footer{margin-top:40px;padding-top:16px;border-top:1px solid #e5e5e5;font-size:12px;color:#888}
@media(prefers-color-scheme:dark){
 body{background:#0c0d10;color:#e7e7ea}a{color:#6f9bff}
 header.site{background:#0a0a0b;border-color:#222}
 .badge{border-color:#333;color:#bbb}.badge.loop{background:#2a140f;border-color:#5a2a1e;color:#ff9b82}
 .crumb,.crumb a,h2{color:#8a8a92}
 table.facts th,table.facts td{border-color:#222}table.facts th{color:#9a9aa2}
 ul.related li,.links a{border-color:#2a2a30}
 footer{border-color:#222;color:#777}.lead{color:#cfcfd6}}
"""


def _entry_page_html(e, payload, rels, by_eid, by_cat, css_href):
    title = f'{e["n"]} — The Lithium Index'
    desc = (e.get("one") or f'{e["n"]} in the {e["s"]} sector.')[:180]
    inner = _entry_content_html(e, payload, rels, by_eid, by_cat)
    # JSON-LD for SEO (Organization/Person, free structured data).
    ld_type = "Person" if e.get("et") == "People" else "Organization"
    ld = {"@context": "https://schema.org", "@type": ld_type, "name": e["n"]}
    if e.get("u"):
        ld["url"] = e["u"]
    if e.get("one"):
        ld["description"] = e["one"]
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{escape(title)}</title>'
        f'<meta name="description" content="{escape(desc)}">'
        f'<link rel="preconnect" href="https://fonts.googleapis.com">'
        f'<style>@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Instrument+Serif:ital@1&family=JetBrains+Mono&display=swap");</style>'
        f'<link rel="stylesheet" href="{escape(css_href)}">'
        f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=True)}</script>'
        f'</head><body>'
        f'<header class="site"><div class="wrap"><span class="brand">link<b>+</b></span>'
        f'<span style="color:#999;font-size:12px">The Lithium Index</span></div></header>'
        f'<div class="wrap"><nav class="crumb"><a href="../index.html">All sectors</a> &#9656; '
        f'{escape(e["s"])} &#9656; {escape(e.get("cn",""))}</nav>'
        f'<h1>{escape(e["n"])}</h1>'
        f'{inner}'
        f'<footer>linkplus.in — every company is a link. '
        f'<a href="../index.html">Browse the full directory &#8599;</a></footer>'
        f'</div></body></html>')


def _blogger_import_xml(payload, rels, by_eid, by_cat):
    """A Blogger/Atom export: import once to create one post per entry.
    Labels = mega-sector + category, so posts are browsable in Blogger."""
    from datetime import datetime
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    head = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom" '
            'xmlns:app="http://www.w3.org/2007/app">\n'
            f'  <title type="text">The Lithium Index</title>\n'
            f'  <updated>{now}</updated>\n')
    parts = [head]
    for idx, e in enumerate(payload["entries"], 1):
        content = _entry_content_html(e, payload, rels, by_eid, by_cat)
        labels = "".join(
            f'    <category scheme="http://www.blogger.com/atom/ns#" term="{escape(t)}"/>\n'
            for t in (e["s"], e.get("cn", "")) if t)
        parts.append(
            '  <entry>\n'
            f'    <id>tag:blogger.com,1999:post-{idx}</id>\n'
            f'    <published>{now}</published>\n'
            f'    <updated>{now}</updated>\n'
            '    <category scheme="http://schemas.google.com/g/2005#kind" '
            'term="http://schemas.google.com/blogger/2008/kind#post"/>\n'
            f'{labels}'
            f'    <title type="text">{escape(e["n"])}</title>\n'
            f'    <content type="html">{escape(content)}</content>\n'
            '    <app:control><app:draft>no</app:draft></app:control>\n'
            '    <author><name>The Lithium Index</name></author>\n'
            '  </entry>\n')
    parts.append('</feed>\n')
    return "".join(parts)


def write_entry_pages(payload, rels):
    """Write dist/e/<slug>.html for every entry + dist/blogger-import.xml."""
    by_eid = {e["eid"]: e for e in payload["entries"]}
    by_cat = {}
    for e in payload["entries"]:
        by_cat.setdefault(e["c"], []).append(e)

    pages_dir = ROOT / "dist" / "e"
    assets_dir = ROOT / "dist" / "assets"
    pages_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "lx-page.css").write_text(PAGE_CSS, encoding="utf-8")

    css_href = "../assets/lx-page.css"
    for e in payload["entries"]:
        html = _entry_page_html(e, payload, rels, by_eid, by_cat, css_href)
        (pages_dir / f'{_entry_slug(e)}.html').write_text(html, encoding="utf-8")
    print(f"[ok] wrote {len(payload['entries'])} entry pages -> {pages_dir}")

    xml = _blogger_import_xml(payload, rels, by_eid, by_cat)
    xml_path = ROOT / "dist" / "blogger-import.xml"
    xml_path.write_text(xml, encoding="utf-8")
    print(f"[ok] wrote {xml_path} ({xml_path.stat().st_size/1024:.0f} KB)")


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

    # ---- Phase 1 metadata: stable IDs, auto-derived base, curated seed, graph
    seen_ids = set()
    for e in entries:
        base = f"E{e['cid']:02d}-{slugify(e['name'])}"
        eid, k = base, 2
        while eid in seen_ids:
            eid = f"{base}-{k}"; k += 1
        seen_ids.add(eid); e["eid"] = eid
        e["et"] = ENTITY_TYPE_BY_CAT.get(e["cid"], "Corporate")
        e["status"] = infer_status(e["name"])
        e["one"] = infer_one_liner(e["name"])

    # index for resolving curated-seed keys -> entry (punctuation-tolerant,
    # longest-prefix, like the URL matcher)
    def norm(s):
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()

    by_norm = {}
    for e in entries:
        by_norm.setdefault(norm(clean_name(e["name"])), e)

    def resolve(key):
        key = norm(key)
        if key in by_norm:
            return by_norm[key]
        hit = hit_cn = None
        for cn, e in by_norm.items():
            if cn.startswith(key + " ") and (hit is None or len(cn) < len(hit_cn)):
                hit, hit_cn = e, cn
        return hit

    # Metadata is sharded: merge every data/metadata/*.json (one file per
    # sector, enriched independently) plus a legacy top-level metadata.json if
    # it still exists. Later files override earlier keys.
    meta_seed = {}
    seed_files = []
    legacy = ROOT / "data" / "metadata.json"
    if legacy.exists():
        seed_files.append(legacy)
    meta_dir = ROOT / "data" / "metadata"
    if meta_dir.is_dir():
        seed_files += sorted(meta_dir.glob("*.json"))
    for f in seed_files:
        for key, fields in json.loads(f.read_text("utf-8")).items():
            if not key.startswith("_"):
                meta_seed[key] = fields
    seed_misses = []
    for key, fields in meta_seed.items():
        if key.startswith("_"):
            continue
        e = resolve(key)
        if not e:
            seed_misses.append(key); continue
        e["meta"] = {k: v for k, v in fields.items()}
        if fields.get("type"):
            e["et"] = fields["type"]
        if fields.get("status"):
            e["status"] = fields["status"]
        if fields.get("one_liner"):
            e["one"] = fields["one_liner"]; e["one_verified"] = True

    rels_doc = json.loads((ROOT / "data" / "relationships.json").read_text("utf-8"))
    rels = {}   # eid -> list of {d:out/in, r:REL, n:name, e:eid}
    rel_misses = []
    seen_edges = set()
    for src, rel, tgt in rels_doc["edges"]:
        a, b = resolve(src), resolve(tgt)
        if not a or not b:
            rel_misses.append((src, rel, tgt)); continue
        sig = (a["eid"], rel, b["eid"])
        if sig in seen_edges:
            continue
        seen_edges.add(sig)
        rels.setdefault(a["eid"], []).append({"d": "out", "r": rel, "n": b["name"], "e": b["eid"]})
        rels.setdefault(b["eid"], []).append({"d": "in", "r": rel, "n": a["name"], "e": a["eid"]})
    if seed_misses:
        print(f"[warn] metadata keys not matched: {seed_misses}")
    if rel_misses:
        print(f"[warn] relationship keys not matched: {rel_misses}")
    print(f"[ok] metadata: {sum(1 for e in entries if e.get('meta'))} seeded, "
          f"{len(rels)} entities with connections, {len(rels_doc['edges'])} edges")

    present_countries = [c for c in COUNTRY_CENTROIDS if any(e["country"] == c for e in entries)]
    payload = {
        "entries": [
            {"i": e["id"], "n": e["name"], "c": e["cid"], "cn": e["cat"],
             "s": e["sector"], "u": e["url"], "t": e["type"], "tech": e["tech"],
             "co": e["country"], "rg": e["region"], "eid": e["eid"], "et": e["et"],
             "stt": e["status"], "one": e["one"],
             **({"lg": e["logo"]} if e.get("logo") else {}),
             **({"ov": 1} if e.get("one_verified") else {}),
             **({"m": e["meta"]} if e.get("meta") else {})}
            for e in entries
        ],
        "rels": rels,
        "tree": tree,
        "colors": {sec: f"var(--c{(i % len(SECTOR_COLORS)) + 1})"
                   for i, sec in enumerate(tree.keys())},
        "types": sorted({e["type"] for e in entries}),
        "techs": sorted({t for e in entries for t in e["tech"]}),
        "gloss": GLOSSARY,
        "stages": (
            [{"n": n, "k": "core", "sectors": secs} for n, secs in LIFECYCLE_STAGES]
            + [{"n": "Links", "k": "links", "sectors": LINKS_SECTORS}]
            + [{"n": "Enablers", "k": "enabler", "sectors": sorted(
                set(tree.keys())
                - {sec for _, ss in LIFECYCLE_STAGES for sec in ss}
                - set(LINKS_SECTORS))}]
        ),
        "countries": sorted({e["country"] for e in entries if e["country"]}),
        "regions": sorted({e["region"] for e in entries if e["region"]}),
        "centroids": {c: COUNTRY_CENTROIDS[c] for c in present_countries},
        "stats": {
            "entries": len(entries),
            "categories": len(categories),
            "sectors": len(tree),
            "withUrl": sum(1 for e in entries if e["url"]),
            "withCountry": sum(1 for e in entries if e["country"]),
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
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

    write_entry_pages(payload, rels)


def _fill(text, payload):
    # ensure_ascii=True so every non-ASCII char is emitted as a \uXXXX escape.
    # Blogger re-encodes literal non-ASCII inside <script> to numeric HTML
    # entities (e.g. ♻ -> &#9851;) which JS cannot decode, printing them
    # literally. \uXXXX escapes are plain ASCII, decode correctly, and survive.
    data_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    stats = payload["stats"]
    light, dark = palette_css()
    return text.replace("/*__DATA__*/", data_json) \
        .replace("/*__PAL__*/", light) \
        .replace("/*__PALD__*/", dark) \
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


def _initials(name):
    base = re.sub(r"\([^)]*\)", " ", name)
    base = re.sub(r"[^A-Za-z0-9 ]", " ", base).strip()
    w = base.split()
    if not w:
        return "?"
    return (w[0][:2] if len(w) == 1 else w[0][0] + w[1][0]).upper()


def _logo_html(entry, color):
    from urllib.parse import urlparse
    # Pinned logo= override wins; else the domain favicon; else a monogram.
    src = entry.get("lg", "")
    if not src and entry.get("u"):
        host = urlparse(entry["u"]).hostname or ""
        if host:
            src = f"https://www.google.com/s2/favicons?domain={host}&sz=64"
    fav = (f'<img class="fav" loading="lazy" alt="" src="{escape(src)}" '
           f'onerror="this.remove()">') if src else ""
    return (f'<span class="logo" style="--sc:{color}">'
            f'<span class="mono">{escape(_initials(entry["n"]))}</span>{fav}</span>')


def _loop_svg_static(payload):
    """Non-interactive Loop for the no-JS Blogger page."""
    import math
    core = [st for st in payload["stages"] if st["k"] == "core"]
    colors = payload["colors"]
    cnt = {st["n"]: sum(1 for e in payload["entries"] if e["s"] in st["sectors"])
           for st in core}
    W, H, cx, cy, r = 900, 470, 450, 232, 150
    seg, gap = 360 / len(core), 18
    pt = lambda a, rr: (cx + rr * math.cos(math.radians(a)),
                        cy + rr * math.sin(math.radians(a)))
    arcs, labels = "", ""
    for i, st in enumerate(core):
        a0, a1 = -90 + i * seg + gap / 2, -90 + (i + 1) * seg - gap / 2
        mid = (a0 + a1) / 2
        (x0, y0), (x1, y1) = pt(a0, r), pt(a1, r)
        col = colors.get(st["sectors"][0], "var(--c1)")
        arcs += (f'<path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 0 1 {x1:.1f} {y1:.1f}" '
                 f'fill="none" stroke="{col}" stroke-width="26"/>')
        lx, ly = pt(mid, r + 42)
        c = math.cos(math.radians(mid))
        anch = "start" if c > .35 else ("end" if c < -.35 else "middle")
        labels += (f'<text class="lp-name" x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anch}">'
                   f'{i+1}· {escape(st["n"])}'
                   f'<tspan class="lp-cnt" dx="7">{cnt[st["n"]]}</tspan></text>')
    total = payload["stats"]["entries"]
    center = (f'<circle cx="{cx}" cy="{cy-34}" r="13" class="lp-ring"/>'
              f'<path d="M {cx} {cy-39.5} v 11 M {cx-5.5} {cy-34} h 11" class="lp-plus"/>'
              f'<text class="lp-center-n" x="{cx}" y="{cy+8}" text-anchor="middle">{total:,}</text>'
              f'<text class="lp-center-l" x="{cx}" y="{cy+26}" text-anchor="middle">COMPANIES LINKED</text>'
              f'<text class="lp-center-l" x="{cx}" y="{cy+42}" text-anchor="middle">THE BATTERY LOOP</text>')
    flow = (f'<g class="lp-flow" aria-hidden="true"><circle r="5" cx="{cx}" '
            f'cy="{cy-r:.1f}" class="lp-flow-dot"/></g>')
    # Static legend: all 12 mega-sectors, grouped by loop role, equal weight.
    seccount = {}
    for e in payload["entries"]:
        seccount[e["s"]] = seccount.get(e["s"], 0) + 1
    ci = 0
    groups = ""
    for st in payload["stages"]:
        if st["k"] == "core":
            ci += 1
            num = f"{ci}· "
        else:
            num = ""
        chips = "".join(
            f'<span class="ll-sec" style="--sc:{colors.get(sec, "var(--c1)")}">'
            f'<span class="dot"></span><span class="ll-nm">{escape(sec)}</span>'
            f'<span class="ll-ct">{seccount.get(sec, 0)}</span></span>'
            for sec in st["sectors"])
        groups += (f'<div class="ll-group ll-{st["k"]}">'
                   f'<div class="ll-role">{num}{escape(st["n"])}</div>'
                   f'<div class="ll-secs">{chips}</div></div>')
    legend = (f'<div class="loop-legend"><div class="ll-h">All 12 mega-sectors — '
              f'every company is a link in the loop</div>'
              f'<div class="ll-groups">{groups}</div></div>')
    return (f'<div class="loop"><svg viewBox="0 0 {W} {H}" class="loopsvg" role="img" '
            f'aria-label="The battery circular economy loop">{arcs}{flow}{labels}{center}</svg>'
            f'{legend}</div>')


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
        tags = "".join(
            f'<span class="tag" title="{escape(GLOSSARY.get(t, t))}">{escape(t)}</span>'
            for t in e["tech"][:3])
        tags = f'<span class="tags">{tags}</span>' if tags else ""
        color = colors.get(e["s"], "#0a0a0a")
        return (
            f'<a class="card{" v" if verified else ""}" '
            f'style="--sc:{color}" href="{escape(href)}" '
            f'target="_blank" rel="noopener">'
            f'<span class="idx">{_logo_html(e, color)}<span class="cid">#{e["i"]}</span>'
            f'<span class="grow"></span>{badge}</span>'
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
        f'<div class="head"><div class="brand"><span class="mark">'
        '<svg class="ic lmark" viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="12" cy="12" r="8.5" stroke-dasharray="8.6 4.7"/>'
        '<path d="M12 8.5v7M8.5 12h7"/></svg></span>'
        f'<h1>The Lithium Index</h1></div>'
        f'<div class="sub">Linking the Battery Circular Economy</div>'
        f'<div class="stat"><b>{n_entries}</b> entries · '
        f'<b>{stats["categories"]}</b> categories · '
        f'<b>{stats["sectors"]}</b> mega-sectors · '
        f'<b>{stats["withUrl"]}</b> verified links</div>'
        f'<div class="tip">Click a sector to expand · '
        f'press Ctrl/⌘+F to search the page</div></div>'
        + _loop_svg_static(payload) +
        f'<div class="toc">{toc}</div>'
        f'<div class="body">{"".join(sections)}</div>'
        f'<div class="foot">The Lithium Index · linkplus.in — every company is a '
        f'link · a ✓ marks a verified official link, others open a web search</div>'
        "</div>\n"
    ).replace("/*__PAL__*/", palette_css()[0])


STYLE_PAGE = r"""<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&display=swap');
#lx{
  --bg:#fafafa; --panel:#fff; --ink:#0a0a0a; --muted:#5f6368; --line:#e4e4e4;
  --ls:#0a0a0a; --blue:#1452ff; --orange:#ff5a1f; --grid:rgba(10,10,10,.035);
  --sans:"Inter",system-ui,-apple-system,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,monospace; --brand:#d92d0a;
  /*__PAL__*/
  container-type:inline-size;
  font-family:var(--sans);
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
#lx .stat,#lx .sub,#lx .tip,#lx .scount,#lx .cid,#lx .idx,#lx .badge,#lx .tag,#lx .toc a,#lx .foot{font-family:var(--mono)}
#lx summary::-webkit-details-marker{display:none}
#lx summary::marker{content:""}
#lx .head{padding:22px 20px; border-bottom:1px solid var(--ls); background:#fff; position:relative}
#lx .head::after{content:""; position:absolute; left:0; right:0; bottom:-1px; height:2px;
  background:linear-gradient(90deg,#2563eb,#7c3aed,#db2777,#ea580c,#f59e0b,#16a34a,#0891b2)}
#lx .loop{background:#fff;border-bottom:1px solid var(--line);padding:16px}
#lx .loopsvg{width:100%;max-width:760px;height:auto;display:block;margin:0 auto}
#lx .lp-name{font-family:var(--sans);font-weight:600;font-size:15px;fill:var(--ink)}
#lx .lp-cnt{font-family:var(--mono);font-size:12px;fill:var(--muted)}
#lx .lp-ring{fill:none;stroke:var(--brand);stroke-width:2;stroke-dasharray:8.2 4.5}
#lx .lp-plus{stroke:var(--brand);stroke-width:2;stroke-linecap:round}
#lx .lp-center-n{font-family:var(--mono);font-weight:700;font-size:30px;fill:var(--ink)}
#lx .lp-center-l{font-family:var(--mono);font-size:9.5px;letter-spacing:.16em;fill:var(--muted)}
#lx .lp-flow{transform-origin:450px 232px;transform-box:view-box;pointer-events:none}
#lx .lp-flow-dot{fill:var(--ink);stroke:#fff;stroke-width:2}
@media(prefers-reduced-motion:no-preference){#lx .lp-flow{animation:lporbit 20s linear infinite}}
@keyframes lporbit{to{transform:rotate(360deg)}}
#lx .loop-legend{margin-top:14px;border-top:1px solid var(--line);padding-top:14px}
#lx .ll-h{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);text-align:center;margin-bottom:12px}
#lx .ll-groups{display:flex;flex-wrap:wrap;gap:12px 16px;justify-content:center;align-items:flex-start}
#lx .ll-group{display:flex;flex-direction:column;gap:6px;min-width:150px}
#lx .ll-role{font-family:var(--mono);font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
#lx .ll-secs{display:flex;flex-direction:column;gap:5px}
#lx .ll-sec{display:inline-flex;align-items:center;gap:7px;font-family:var(--sans);font-size:12px;border:1px solid var(--line);padding:6px 9px;color:var(--ink);width:100%;box-sizing:border-box}
#lx .ll-sec .dot{width:8px;height:8px;border-radius:50%;background:var(--sc);flex:none}
#lx .ll-nm{flex:1}
#lx .ll-ct{font-family:var(--mono);font-size:11px;color:var(--muted)}
#lx .brand{display:flex; align-items:baseline; gap:10px}
#lx .mark{display:inline-flex; color:var(--brand); transform:translateY(3px)}
#lx .ic{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:2;
  stroke-linecap:round;stroke-linejoin:round;vertical-align:-2px}
#lx .mark .ic{width:24px;height:20px;stroke-width:1.8}
#lx .mark .bolt{stroke:var(--orange)}
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
#lx .card{display:flex; flex-direction:column; gap:9px; border:1px solid var(--ls);
  border-top:3px solid var(--sc,var(--ls));
  background:#fff; padding:16px; min-height:112px; transition:box-shadow 160ms cubic-bezier(.2,.7,.4,1)}
#lx .card.v{box-shadow:inset 3px 0 0 var(--blue)}
#lx .card:hover{box-shadow:4px 4px 0 var(--ink)}
#lx .card.v:hover{box-shadow:4px 4px 0 var(--ink),inset 3px 0 0 var(--blue)}
#lx .idx{display:flex; align-items:center; gap:8px}
#lx .cid{font-size:9px; color:var(--muted); letter-spacing:.1em}
#lx .grow{flex:1}
#lx .logo{position:relative; width:30px; height:30px; flex:0 0 auto; border:1px solid var(--line); overflow:hidden}
#lx .logo .mono{position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
  font-size:11px; font-weight:700; color:#fff; background:var(--sc,var(--ls))}
#lx .logo .fav{position:absolute; inset:0; width:100%; height:100%; object-fit:contain; background:#fff; padding:3px}
#lx .badge{font-size:9px; letter-spacing:.12em; color:#fff; background:var(--blue); border:1px solid var(--blue); padding:1px 5px}
#lx .nm{font-family:var(--sans); font-weight:600; font-size:14px;
  line-height:1.4; letter-spacing:-.1px; flex:1; overflow-wrap:anywhere; word-break:break-word}
#lx .tags{display:flex; flex-wrap:wrap; gap:4px}
#lx .tag{font-size:9px; color:#444; background:#f1f3ff; border:1px solid #d6ddff; padding:2px 6px;
  cursor:help; text-decoration:underline dotted; text-underline-offset:2px}
#lx .go{font-size:10px; color:var(--muted); border-top:1px solid var(--line); padding-top:8px}
#lx .card:hover .go{color:var(--orange)}
#lx .top{display:block; text-align:right; font-size:10px; color:var(--blue); padding:8px 4px 2px}
#lx .foot{padding:20px; border-top:1px solid var(--ls); color:var(--muted); font-size:10px; background:#fff}
@container (max-width:440px){ #lx h1{font-size:24px} }
</style>"""


STYLE_EMBED = r"""<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&display=swap');
#li-root{
  --bg:#fafafa; --panel:#ffffff; --ink:#0a0a0a; --muted:#5f6368;
  --line:#e4e4e4; --line-strong:#0a0a0a; --blue:#1452ff; --orange:#ff5a1f;
  --grid:rgba(10,10,10,.035); --cell:48px;
  --sans:"Inter",system-ui,-apple-system,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,monospace;
  --fs-label:10px; --fs-body:13px; --fs-title:15px; --fs-display:26px;
  --ease:cubic-bezier(.2,.7,.4,1); --speed:160ms; --brand:#d92d0a;
  /*__PAL__*/
  container-type:inline-size;
  font-family:var(--sans);
  color:var(--ink); font-size:13px; line-height:1.5; text-align:left;
  background:var(--bg);
  background-image:linear-gradient(var(--grid) 1px,transparent 1px),
                   linear-gradient(90deg,var(--grid) 1px,transparent 1px);
  background-size:var(--cell) var(--cell);
  border:1px solid var(--line-strong);
  box-sizing:border-box; overflow:hidden;
  /* Break out of the theme's (often narrow) content column and use the
     viewport width, capped, so the directory actually widens on big screens.
     Assumes a centered content column (the Blogger norm). No transform, so
     the fixed drawer still anchors to the viewport; inner content is capped. */
  position:relative; left:50%; right:50%; width:100vw;
  margin:18px -50vw;
  -webkit-font-smoothing:antialiased;
}
#li-root *{box-sizing:border-box; margin:0; padding:0}
#li-root .bar,#li-root .wrap,#li-root footer{max-width:1500px;margin-left:auto;margin-right:auto}
#li-root a{color:inherit;text-decoration:none}
#li-root .stats,#li-root .ct,#li-root .cid,#li-root .kbd,#li-root .sec,#li-root .aside-h,
#li-root .resultline,#li-root .idx,#li-root .badge,#li-root .tag,#li-root .chip,
#li-root .tile-c,#li-root .tile-sub,#li-root .search input,#li-root .d-sec,#li-root .d-h{font-family:var(--mono)}
#li-root .ic{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:2;
  stroke-linecap:round;stroke-linejoin:round;vertical-align:-2px;flex:0 0 auto}
#li-root .tw .ic{width:10px;height:10px}
#li-root .viewtabs .ic,#li-root .hbtn .ic{margin-right:5px}
#li-root .chip .x .ic,#li-root .d-x .ic{width:11px;height:11px}
#li-root .go .ic{width:11px;height:11px;margin-right:5px}
#li-root .batt-empty{width:46px;height:46px;fill:none;stroke:var(--muted);stroke-width:1.6;
  stroke-linecap:round;stroke-linejoin:round;display:block;margin:0 auto 12px}
#li-root button,#li-root input,#li-root select{font-family:inherit}
#li-root .menu-toggle{display:none !important}
#li-root h1{font-size:26px;font-weight:400}

#li-root header{display:block;position:sticky;top:0;z-index:40;background:#fff;border-bottom:1px solid var(--line-strong)}
#li-root header::after{content:"";position:absolute;left:0;right:0;bottom:-1px;height:2px;
  background:linear-gradient(90deg,#2563eb,#7c3aed,#db2777,#ea580c,#f59e0b,#16a34a,#0891b2)}
#li-root .bar{padding:14px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
#li-root .brand{display:flex;align-items:baseline;gap:10px;white-space:nowrap}
#li-root .brand .mark{display:inline-flex;color:var(--brand);transform:translateY(2px)}
#li-root .brand .mark .ic{width:22px;height:18px;stroke-width:1.8}
#li-root .brand .mark .bolt{stroke:var(--orange)}
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
#li-root .sector>.row.on{background:var(--sc,var(--ink));color:#fff}
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
#li-root .toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:18px}
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
#li-root .chip .x{cursor:pointer;color:var(--muted);font-weight:700}
#li-root .chip .x:hover{color:var(--orange)}
#li-root .resultline{font-size:11px;color:var(--muted);margin-bottom:10px;letter-spacing:.04em}
#li-root .resultline b{color:var(--ink)}
#li-root .crumb{font-family:var(--mono);font-size:11px;color:var(--muted);margin-bottom:10px;
  display:flex;align-items:center;gap:7px;flex-wrap:wrap}
#li-root .crumb a{color:var(--blue);cursor:pointer}
#li-root .crumb a:hover{text-decoration:underline}
#li-root .crumb b{color:var(--ink);font-weight:600}
#li-root .crumb .sep{color:var(--muted)}
#li-root .search .sug{position:absolute;top:100%;left:0;right:0;z-index:90;background:var(--panel);
  border:1px solid var(--line-strong);border-top:0;max-height:330px;overflow:auto;
  box-shadow:4px 4px 0 rgba(10,10,10,.12)}
#li-root .sug button{display:flex;width:100%;gap:9px;align-items:center;padding:9px 12px;
  font-family:var(--sans);font-size:12.5px;background:none;border:0;
  border-bottom:1px solid var(--line);cursor:pointer;text-align:left;color:var(--ink)}
#li-root .sug button:last-child{border-bottom:0}
#li-root .sug button:hover,#li-root .sug button.on{background:rgba(20,82,255,.07)}
#li-root .sug .k{font-family:var(--mono);font-size:9px;letter-spacing:.1em;color:#fff;
  background:var(--ink);padding:2px 5px;flex:0 0 auto}
#li-root .sug .k.kc{background:var(--blue)}
#li-root .sug .sn{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#li-root .sug .cnt{margin-left:auto;font-family:var(--mono);font-size:10px;color:var(--muted)}

#li-root .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:16px}
#li-root .card{background:var(--panel);border:1px solid var(--line-strong);padding:18px 18px 15px;
  display:flex;flex-direction:column;gap:10px;min-height:128px;
  transition:transform var(--speed) var(--ease), box-shadow var(--speed) var(--ease);position:relative;overflow:hidden}
#li-root .card:hover{transform:translate(-2px,-2px);box-shadow:4px 4px 0 var(--ink)}
#li-root .card .nm{font-family:var(--sans);font-weight:600;
  font-size:14px;line-height:1.4;letter-spacing:-.1px;flex:1;
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
#li-root .card .idx{display:flex;align-items:center;gap:8px}
#li-root .card .cid{font-size:9px;color:var(--muted);letter-spacing:.1em}
#li-root .card .grow{flex:1}
#li-root .logo{position:relative;width:30px;height:30px;flex:0 0 auto;border:1px solid var(--line);overflow:hidden}
#li-root .logo .mono{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:700;color:#fff;background:var(--sc,var(--ink))}
#li-root .logo .fav{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#fff;padding:3px}
#li-root .badge{font-size:9px;letter-spacing:.12em;color:#fff;background:var(--blue);
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
#li-root .pager button.on{background:var(--blue);border-color:var(--blue);color:#fff}
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
#li-root .hactions{display:flex;align-items:center;gap:8px}
#li-root .hbtn{font-family:inherit;font-size:11px;background:var(--panel);color:var(--ink);
  border:1px solid var(--line-strong);padding:7px 10px;cursor:pointer}
#li-root .hbtn:hover{background:#f0f0f0}
#li-root .hbtn.icon{padding:6px 9px;font-size:13px;line-height:1}
#li-root .viewtabs{display:flex;border:1px solid var(--line-strong)}
#li-root .viewtabs button{font-family:inherit;font-size:11px;background:var(--panel);color:var(--ink);
  border:0;border-right:1px solid var(--line-strong);padding:6px 10px;cursor:pointer;white-space:nowrap}
#li-root .viewtabs button:last-child{border-right:0}
#li-root .viewtabs button.on{background:var(--blue);color:#fff}
#li-root .landscape .tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}
#li-root .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:16px;margin-bottom:16px}
#li-root .kpi{background:var(--panel);border:1px solid var(--line-strong);padding:14px 16px}
#li-root .kpi b{display:block;font-family:var(--mono);font-size:24px;font-weight:700;line-height:1.15}
#li-root .kpi span{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
#li-root .secbar{background:var(--panel);border:1px solid var(--line-strong);padding:16px 18px;margin-bottom:16px}
#li-root .secbar-h{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}
#li-root .sbrow{display:flex;align-items:center;gap:10px;width:100%;background:none;border:0;
  padding:3px 0;cursor:pointer;font-family:var(--sans);font-size:12px;color:var(--ink)}
#li-root .sbrow:hover .sbn{color:var(--blue)}
#li-root .sbn{flex:0 0 230px;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#li-root .sbtrack{flex:1;height:8px}
#li-root .sbfill{display:block;height:100%;border-radius:0 4px 4px 0;min-width:2px}
#li-root .sbv{flex:0 0 46px;text-align:left;font-family:var(--mono);font-size:11px;color:var(--muted)}
@container (max-width:700px){#li-root .sbn{flex-basis:120px;font-size:11px}
  #li-root .lp-name{font-size:22px}#li-root .lp-cnt{font-size:18px}#li-root .lp-ret-t{font-size:16px}
  #li-root .lp-center-n{font-size:40px}#li-root .lp-center-l{font-size:14px}}
#li-root .loop{background:var(--panel);border:1px solid var(--line-strong);padding:14px 16px 16px;margin-bottom:16px}
#li-root .loopsvg{width:100%;max-width:820px;height:auto;display:block;margin:0 auto}
#li-root .lp-stage{cursor:pointer}
#li-root .lp-stage path{transition:stroke-width var(--speed) var(--ease)}
#li-root .lp-stage:hover path:last-child,#li-root .lp-stage:focus-visible path:last-child{stroke-width:34}
#li-root .lp-link{cursor:pointer;fill:var(--muted)}
#li-root .lp-link:hover{fill:var(--blue)}
#li-root .lp-name{font-family:var(--sans);font-weight:600;font-size:15px;fill:var(--ink)}
#li-root .lp-cnt{font-family:var(--mono);font-weight:400;font-size:12px;fill:var(--muted)}
#li-root .lp-ret,#li-root .lp-name,#li-root .lp-center,#li-root .lp-flow{pointer-events:none}
#li-root .lp-ret path{stroke:var(--brand);stroke-width:2;stroke-dasharray:6 5}
#li-root .lp-flow{transform-origin:450px 232px;transform-box:view-box}
#li-root .lp-flow-dot{fill:var(--ink);stroke:var(--panel);stroke-width:2}
@media(prefers-reduced-motion:no-preference){
  #li-root .lp-flow{animation:lporbit 20s linear infinite}
  #li-root .lp-ret path{animation:lpflow 1.1s linear infinite}
}
@keyframes lporbit{to{transform:rotate(360deg)}}
@keyframes lpflow{to{stroke-dashoffset:-11}}
#li-root .lp-ret-head{fill:var(--brand)}
#li-root .lp-ret-t{font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;fill:var(--brand)}
#li-root .lp-ring{fill:none;stroke:var(--brand);stroke-width:2;stroke-dasharray:8.2 4.5}
#li-root .lp-plus{stroke:var(--brand);stroke-width:2;stroke-linecap:round}
#li-root .lp-center-n{font-family:var(--mono);font-weight:700;font-size:30px;fill:var(--ink)}
#li-root .lp-center-l{font-family:var(--mono);font-size:9.5px;letter-spacing:.16em;fill:var(--muted)}
#li-root .loop-legend{margin-top:14px;border-top:1px solid var(--line);padding-top:14px}
#li-root .ll-h{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);text-align:center;margin-bottom:12px}
#li-root .ll-groups{display:flex;flex-wrap:wrap;gap:12px 16px;justify-content:center;align-items:flex-start}
#li-root .ll-group{display:flex;flex-direction:column;gap:6px;min-width:150px}
#li-root .ll-role{font-family:var(--mono);font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
#li-root .ll-role[data-stage],#li-root .ll-role[data-sector]{cursor:pointer}
#li-root .ll-role[data-stage]:hover,#li-root .ll-role[data-sector]:hover{color:var(--ink)}
#li-root .ll-secs{display:flex;flex-direction:column;gap:5px}
#li-root .ll-sec{display:inline-flex;align-items:center;gap:7px;font-family:var(--sans);font-size:12px;background:none;border:1px solid var(--line);padding:6px 9px;cursor:pointer;color:var(--ink);text-align:left;width:100%}
#li-root .ll-sec:hover{border-color:var(--sc);color:var(--sc)}
#li-root .ll-sec .dot{width:8px;height:8px;border-radius:50%;background:var(--sc);flex:none}
#li-root .ll-nm{flex:1}
#li-root .ll-ct{font-family:var(--mono);font-size:11px;color:var(--muted)}
#li-root .ll-sec:hover .ll-ct{color:var(--sc)}
#li-root .d-sec .dot{width:7px;height:7px;border-radius:50%;background:var(--sc,var(--muted));flex:0 0 auto}
#li-root .tile{text-align:left;font-family:inherit;cursor:pointer;background:var(--panel);
  border:1px solid var(--line-strong);border-top:4px solid var(--sc,var(--ink));
  padding:14px;display:flex;flex-direction:column;gap:8px;color:var(--ink);
  transition:transform var(--speed) var(--ease),box-shadow var(--speed) var(--ease)}
#li-root .tile:hover{transform:translate(-2px,-2px);box-shadow:5px 5px 0 var(--sc,var(--ink))}
#li-root .tile-h{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
#li-root .tile-n{font-weight:700;font-size:14px;line-height:1.25}
#li-root .tile-c{font-size:16px;font-weight:700;color:var(--sc,var(--ink))}
#li-root .tile-sub{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
#li-root .tile-top{font-size:10.5px;color:var(--muted);line-height:1.5}
#li-root .mapwrap{border:1px solid var(--line-strong);background:var(--panel);padding:8px}
#li-root .worldmap{width:100%;height:auto;display:block}
#li-root .worldmap .ocean{fill:transparent}
#li-root .worldmap .grat{stroke:var(--line);stroke-width:1}
#li-root .worldmap .guide{fill:var(--muted);font-size:13px;letter-spacing:.18em;text-anchor:middle;opacity:.45}
#li-root .worldmap .bub{cursor:pointer}
#li-root .worldmap .bub circle{transition:fill-opacity .1s}
#li-root .worldmap .bub:hover circle{fill-opacity:.85}
#li-root .worldmap .bub-n{fill:var(--ink);font-size:11px;text-anchor:middle;pointer-events:none}
#li-root .worldmap .bub.on .bub-n{font-weight:700}
#li-root .drawer{position:fixed;inset:0;z-index:2000}
#li-root .drawer[hidden]{display:none}
#li-root .drawer .scrim{position:absolute;inset:0;background:rgba(0,0,0,.35);opacity:0;transition:opacity .2s}
#li-root .drawer.open .scrim{opacity:1}
#li-root .drawer .panel{position:absolute;top:0;right:0;height:100%;width:min(420px,92vw);
  background:var(--panel);border-left:1px solid var(--line-strong);box-shadow:-8px 0 24px rgba(0,0,0,.15);
  padding:18px;overflow:auto;transform:translateX(100%);transition:transform .2s;
  display:flex;flex-direction:column;gap:12px}
#li-root .drawer.open .panel{transform:none}
#li-root .d-top{display:flex;align-items:flex-start;gap:10px}
#li-root .d-top .logo{width:38px;height:38px}
#li-root .d-title{flex:1;min-width:0}
#li-root .d-title h3{font-family:"Instrument Serif",Georgia,serif;font-style:italic;font-weight:400;
  font-size:22px;line-height:1.15;overflow-wrap:anywhere}
#li-root .d-sec{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);
  display:flex;align-items:center;gap:5px;margin-top:4px}
#li-root .d-x{background:none;border:0;font-family:inherit;font-size:14px;cursor:pointer;color:var(--muted)}
#li-root .d-cat{font-size:11px;color:var(--blue);cursor:pointer}
#li-root .d-cat:hover{text-decoration:underline}
#li-root .d-links{display:flex;flex-wrap:wrap;gap:6px}
#li-root .d-link{font-size:11px;border:1px solid var(--line-strong);padding:6px 9px;color:var(--ink)}
#li-root .d-link:hover{background:#f0f0f0}
#li-root .d-link.primary{background:var(--blue);border-color:var(--blue);color:#fff}
#li-root .d-h{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);
  border-top:1px solid var(--line);padding-top:12px}
#li-root .d-related{display:flex;flex-direction:column;gap:4px}
#li-root .d-rel{display:flex;align-items:center;gap:8px;text-align:left;font-family:inherit;font-size:12px;
  background:none;border:1px solid var(--line);padding:6px;cursor:pointer;color:var(--ink)}
#li-root .d-rel:hover{background:#f4f4f4}
#li-root .d-rel .logo{width:22px;height:22px}
#li-root .d-rel span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#li-root .d-empty{font-size:11px;color:var(--muted)}
#li-root .d-suggest{font-size:11px;color:var(--blue);margin-top:4px}
#li-root .d-one{font-size:13px;line-height:1.5;color:var(--ink);font-style:italic}
#li-root .d-inf{font-family:var(--mono);font-size:8px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--muted);border:1px solid var(--line);padding:1px 4px;vertical-align:1px}
#li-root .d-facts{display:flex;flex-direction:column;gap:6px}
#li-root .d-fact{display:flex;gap:10px;font-size:12px;line-height:1.4}
#li-root .d-fact .fk{flex:0 0 116px;color:var(--muted);font-family:var(--mono);font-size:10px;
  letter-spacing:.04em;text-transform:uppercase;padding-top:1px}
#li-root .d-fact .fv{flex:1;color:var(--ink);overflow-wrap:anywhere}
#li-root .d-n{font-family:var(--mono);font-size:10px;color:var(--muted);border:1px solid var(--line);padding:0 5px}
#li-root .d-conns{display:flex;flex-direction:column;gap:4px}
#li-root .d-conn{display:flex;flex-direction:column;gap:1px;text-align:left;font-family:var(--sans);
  background:none;border:1px solid var(--line);border-left:3px solid var(--blue);
  padding:6px 9px;cursor:pointer;color:var(--ink)}
#li-root .d-conn:hover{background:rgba(20,82,255,.06)}
#li-root .d-conn .cr{font-family:var(--mono);font-size:9px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
#li-root .d-conn .cn2{font-size:12px;font-weight:500}
#li-root mark{color:#111}
#li-root :focus-visible{outline:2px solid var(--blue);outline-offset:2px}
#li-root .pill:active,#li-root .sort:active,#li-root .hbtn:active,#li-root .viewtabs button:active,
#li-root .pager button:active,#li-root .tile:active,#li-root .sbrow:active{transform:translateY(1px)}
#li-root .tag{cursor:help;text-decoration:underline dotted;text-underline-offset:2px;text-decoration-thickness:1px}
@container (max-width:679px){
  #li-root .sector>.row{min-height:44px}
  #li-root .cat{min-height:40px;align-items:center}
  #li-root .pill,#li-root .sort,#li-root .hbtn,#li-root .viewtabs button{min-height:40px}
  #li-root .pager button{min-height:42px;min-width:44px}
}
#li-root[data-theme=dark]{--bg:#0c0d10;--panel:#15171c;--ink:#e8e8ea;--muted:#9aa1ab;
  --line:#262a31;--line-strong:#3a3f48;--grid:rgba(255,255,255,.035);/*__PALD__*/}
#li-root[data-theme=dark] .hbtn:hover,#li-root[data-theme=dark] .d-link:hover,
#li-root[data-theme=dark] .pill:hover,#li-root[data-theme=dark] .d-rel:hover,
#li-root[data-theme=dark] .sort:hover,#li-root[data-theme=dark] .cat:hover,
#li-root[data-theme=dark] .pager button:hover:not(:disabled){background:#22252c}
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
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#fafafa; --panel:#ffffff; --ink:#0a0a0a; --muted:#5f6368;
  --line:#e4e4e4; --line-strong:#0a0a0a;
  --blue:#1452ff; --orange:#ff5a1f;
  --grid:rgba(10,10,10,.03); --cell:48px;
  --maxw:1560px;
  --sans:"Inter",system-ui,-apple-system,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,monospace;
  --fs-label:10px; --fs-body:13px; --fs-title:15px; --fs-display:26px;
  --ease:cubic-bezier(.2,.7,.4,1); --speed:160ms; --brand:#d92d0a;
  /*__PAL__*/
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:var(--sans);
  background:var(--bg); color:var(--ink); font-size:var(--fs-body); line-height:1.5;
  background-image:linear-gradient(var(--grid) 1px,transparent 1px),
                   linear-gradient(90deg,var(--grid) 1px,transparent 1px);
  background-size:var(--cell) var(--cell);
  -webkit-font-smoothing:antialiased;
}
a{color:inherit;text-decoration:none}
.stats,.ct,.cid,.kbd,.sec,.aside-h,.resultline,.idx,.badge,.tag,.chip,
.tile-c,.tile-sub,.search input,.d-sec,.d-h{font-family:var(--mono)}
.ic{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:2;
  stroke-linecap:round;stroke-linejoin:round;vertical-align:-2px;flex:0 0 auto}
.tw .ic{width:10px;height:10px}
.viewtabs .ic,.hbtn .ic{margin-right:5px}
.chip .x .ic,.d-x .ic{width:11px;height:11px}
.go .ic{width:11px;height:11px;margin-right:5px}

/* ---------- header ---------- */
header{
  position:sticky;top:0;z-index:50;background:rgba(250,250,250,.86);
  backdrop-filter:blur(10px);border-bottom:1px solid var(--line-strong);
}
header::after{content:"";position:absolute;left:0;right:0;bottom:-1px;height:2px;
  background:linear-gradient(90deg,#2563eb,#7c3aed,#db2777,#ea580c,#f59e0b,#16a34a,#0891b2)}
.bar{max-width:var(--maxw);margin:0 auto;padding:14px 20px;
  display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.brand{display:flex;align-items:baseline;gap:10px;white-space:nowrap}
.brand .mark{display:inline-flex;color:var(--brand);transform:translateY(2px)}
.brand .mark .ic{width:22px;height:18px;stroke-width:1.8}
.brand .mark .bolt{stroke:var(--orange)}
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
.sector>.row.on{background:var(--sc,var(--ink));color:#fff}
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
.toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:18px}
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
.chip .x{cursor:pointer;color:var(--muted);font-weight:700}
.chip .x:hover{color:var(--orange)}
.resultline{font-size:11px;color:var(--muted);margin-bottom:10px;
  letter-spacing:.04em}
.resultline b{color:var(--ink)}
.crumb{font-family:var(--mono);font-size:11px;color:var(--muted);margin-bottom:10px;
  display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.crumb a{color:var(--blue);cursor:pointer}
.crumb a:hover{text-decoration:underline}
.crumb b{color:var(--ink);font-weight:600}
.crumb .sep{color:var(--muted)}
.search .sug{position:absolute;top:100%;left:0;right:0;z-index:90;background:var(--panel);
  border:1px solid var(--line-strong);border-top:0;max-height:330px;overflow:auto;
  box-shadow:4px 4px 0 rgba(10,10,10,.12)}
.sug button{display:flex;width:100%;gap:9px;align-items:center;padding:9px 12px;
  font-family:var(--sans);font-size:12.5px;background:none;border:0;
  border-bottom:1px solid var(--line);cursor:pointer;text-align:left;color:var(--ink)}
.sug button:last-child{border-bottom:0}
.sug button:hover,.sug button.on{background:rgba(20,82,255,.07)}
.sug .k{font-family:var(--mono);font-size:9px;letter-spacing:.1em;color:#fff;
  background:var(--ink);padding:2px 5px;flex:0 0 auto}
.sug .k.kc{background:var(--blue)}
.sug .sn{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sug .cnt{margin-left:auto;font-family:var(--mono);font-size:10px;color:var(--muted)}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}
.card{background:var(--panel);border:1px solid var(--line-strong);padding:18px 18px 15px;
  display:flex;flex-direction:column;gap:10px;min-height:128px;
  transition:transform var(--speed) var(--ease), box-shadow var(--speed) var(--ease);position:relative;overflow:hidden}
.card:hover{transform:translate(-2px,-2px);box-shadow:4px 4px 0 var(--ink)}
.card .idx{font-size:9px;color:var(--muted);letter-spacing:.1em}
.card .nm{font-family:var(--sans);font-weight:600;
  font-size:14px;line-height:1.4;letter-spacing:-.1px;flex:1;
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
.card .idx{display:flex;align-items:center;gap:8px}
.card .cid{font-size:9px;color:var(--muted);letter-spacing:.1em}
.card .grow{flex:1}
.logo{position:relative;width:30px;height:30px;flex:0 0 auto;border:1px solid var(--line);overflow:hidden}
.logo .mono{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:700;color:#fff;background:var(--sc,var(--ink))}
.logo .fav{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#fff;padding:3px}
.badge{font-size:9px;letter-spacing:.12em;color:#fff;background:var(--blue);
  border:1px solid var(--blue);padding:1px 5px}
.tags{display:flex;flex-wrap:wrap;gap:4px}
.tag{font-size:9px;letter-spacing:.04em;color:#444;background:#f1f3ff;
  border:1px solid #d6ddff;padding:2px 6px}
mark{background:linear-gradient(transparent 55%, #ffe08a 55%);color:inherit;padding:0}

.empty{padding:60px 20px;text-align:center;color:var(--muted);
  border:1px dashed var(--line-strong);background:var(--panel)}
.empty b{display:block;font-size:18px;color:var(--ink);margin-bottom:6px}
.batt-empty{width:46px;height:46px;fill:none;stroke:var(--muted);stroke-width:1.6;
  stroke-linecap:round;stroke-linejoin:round;display:block;margin:0 auto 12px}

.pager{display:flex;align-items:center;justify-content:center;gap:6px;
  margin:26px 0 8px;flex-wrap:wrap}
.pager button{font-family:inherit;font-size:11px;background:var(--panel);
  border:1px solid var(--line-strong);padding:7px 12px;cursor:pointer;min-width:38px}
.pager button:hover:not(:disabled){background:#f0f0f0}
.pager button.on{background:var(--blue);border-color:var(--blue);color:#fff}
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

/* header actions, view tabs */
.hactions{display:flex;align-items:center;gap:8px}
.hbtn{font-family:inherit;font-size:11px;background:var(--panel);color:var(--ink);
  border:1px solid var(--line-strong);padding:7px 10px;cursor:pointer}
.hbtn:hover{background:#f0f0f0}
.hbtn.icon{padding:6px 9px;font-size:13px;line-height:1}
.viewtabs{display:flex;border:1px solid var(--line-strong)}
.viewtabs button{font-family:inherit;font-size:11px;background:var(--panel);color:var(--ink);
  border:0;border-right:1px solid var(--line-strong);padding:6px 10px;cursor:pointer;white-space:nowrap}
.viewtabs button:last-child{border-right:0}
.viewtabs button.on{background:var(--blue);color:#fff}
/* landscape tiles */
.landscape .tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:16px;margin-bottom:16px}
.kpi{background:var(--panel);border:1px solid var(--line-strong);padding:14px 16px}
.kpi b{display:block;font-family:var(--mono);font-size:24px;font-weight:700;line-height:1.15}
.kpi span{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.secbar{background:var(--panel);border:1px solid var(--line-strong);padding:16px 18px;margin-bottom:16px}
.secbar-h{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}
.sbrow{display:flex;align-items:center;gap:10px;width:100%;background:none;border:0;
  padding:3px 0;cursor:pointer;font-family:var(--sans);font-size:12px;color:var(--ink)}
.sbrow:hover .sbn{color:var(--blue)}
.sbn{flex:0 0 230px;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sbtrack{flex:1;height:8px}
.sbfill{display:block;height:100%;border-radius:0 4px 4px 0;min-width:2px}
.sbv{flex:0 0 46px;text-align:left;font-family:var(--mono);font-size:11px;color:var(--muted)}
@media(max-width:700px){.sbn{flex-basis:120px;font-size:11px}
  .lp-name{font-size:22px}.lp-cnt{font-size:18px}.lp-ret-t{font-size:16px}
  .lp-center-n{font-size:40px}.lp-center-l{font-size:14px}}
.loop{background:var(--panel);border:1px solid var(--line-strong);padding:14px 16px 16px;margin-bottom:16px}
.loopsvg{width:100%;max-width:820px;height:auto;display:block;margin:0 auto}
.lp-stage{cursor:pointer}
.lp-stage path{transition:stroke-width var(--speed) var(--ease)}
.lp-stage:hover path:last-child,.lp-stage:focus-visible path:last-child{stroke-width:34}
.lp-link{cursor:pointer;fill:var(--muted)}
.lp-link:hover{fill:var(--blue)}
.lp-name{font-family:var(--sans);font-weight:600;font-size:15px;fill:var(--ink)}
.lp-cnt{font-family:var(--mono);font-weight:400;font-size:12px;fill:var(--muted)}
.lp-ret,.lp-name,.lp-center,.lp-flow{pointer-events:none}
.lp-ret path{stroke:var(--brand);stroke-width:2;stroke-dasharray:6 5}
.lp-flow{transform-origin:450px 232px;transform-box:view-box}
.lp-flow-dot{fill:var(--ink);stroke:var(--panel);stroke-width:2}
@media(prefers-reduced-motion:no-preference){
  .lp-flow{animation:lporbit 20s linear infinite}
  .lp-ret path{animation:lpflow 1.1s linear infinite}
}
@keyframes lporbit{to{transform:rotate(360deg)}}
@keyframes lpflow{to{stroke-dashoffset:-11}}
.lp-ret-head{fill:var(--brand)}
.lp-ret-t{font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;fill:var(--brand)}
.lp-ring{fill:none;stroke:var(--brand);stroke-width:2;stroke-dasharray:8.2 4.5}
.lp-plus{stroke:var(--brand);stroke-width:2;stroke-linecap:round}
.lp-center-n{font-family:var(--mono);font-weight:700;font-size:30px;fill:var(--ink)}
.lp-center-l{font-family:var(--mono);font-size:9.5px;letter-spacing:.16em;fill:var(--muted)}
.loop-legend{margin-top:14px;border-top:1px solid var(--line);padding-top:14px}
.ll-h{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);text-align:center;margin-bottom:12px}
.ll-groups{display:flex;flex-wrap:wrap;gap:12px 16px;justify-content:center;align-items:flex-start}
.ll-group{display:flex;flex-direction:column;gap:6px;min-width:150px}
.ll-role{font-family:var(--mono);font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.ll-role[data-stage],.ll-role[data-sector]{cursor:pointer}
.ll-role[data-stage]:hover,.ll-role[data-sector]:hover{color:var(--ink)}
.ll-secs{display:flex;flex-direction:column;gap:5px}
.ll-sec{display:inline-flex;align-items:center;gap:7px;font-family:var(--sans);font-size:12px;background:none;border:1px solid var(--line);padding:6px 9px;cursor:pointer;color:var(--ink);text-align:left;width:100%}
.ll-sec:hover{border-color:var(--sc);color:var(--sc)}
.ll-sec .dot{width:8px;height:8px;border-radius:50%;background:var(--sc);flex:none}
.ll-nm{flex:1}
.ll-ct{font-family:var(--mono);font-size:11px;color:var(--muted)}
.ll-sec:hover .ll-ct{color:var(--sc)}
.d-sec .dot{width:7px;height:7px;border-radius:50%;background:var(--sc,var(--muted));flex:0 0 auto}
.tile{text-align:left;font-family:inherit;cursor:pointer;background:var(--panel);
  border:1px solid var(--line-strong);border-top:4px solid var(--sc,var(--ink));
  padding:14px;display:flex;flex-direction:column;gap:8px;color:var(--ink);
  transition:transform var(--speed) var(--ease),box-shadow var(--speed) var(--ease)}
.tile:hover{transform:translate(-2px,-2px);box-shadow:5px 5px 0 var(--sc,var(--ink))}
.tile-h{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.tile-n{font-weight:700;font-size:14px;line-height:1.25}
.tile-c{font-size:16px;font-weight:700;color:var(--sc,var(--ink))}
.tile-sub{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.tile-top{font-size:10.5px;color:var(--muted);line-height:1.5}
/* world map */
.mapwrap{border:1px solid var(--line-strong);background:var(--panel);padding:8px}
.worldmap{width:100%;height:auto;display:block}
.worldmap .ocean{fill:transparent}
.worldmap .grat{stroke:var(--line);stroke-width:1}
.worldmap .guide{fill:var(--muted);font-size:13px;letter-spacing:.18em;text-anchor:middle;opacity:.45}
.worldmap .bub{cursor:pointer}
.worldmap .bub circle{transition:fill-opacity .1s}
.worldmap .bub:hover circle{fill-opacity:.85}
.worldmap .bub-n{fill:var(--ink);font-size:11px;text-anchor:middle;pointer-events:none}
.worldmap .bub.on .bub-n{font-weight:700}
/* detail drawer */
.drawer{position:fixed;inset:0;z-index:200}
.drawer[hidden]{display:none}
.drawer .scrim{position:absolute;inset:0;background:rgba(0,0,0,.35);opacity:0;transition:opacity .2s}
.drawer.open .scrim{opacity:1}
.drawer .panel{position:absolute;top:0;right:0;height:100%;width:min(420px,92vw);
  background:var(--panel);border-left:1px solid var(--line-strong);box-shadow:-8px 0 24px rgba(0,0,0,.15);
  padding:18px;overflow:auto;transform:translateX(100%);transition:transform .2s;
  display:flex;flex-direction:column;gap:12px}
.drawer.open .panel{transform:none}
.d-top{display:flex;align-items:flex-start;gap:10px}
.d-top .logo{width:38px;height:38px}
.d-title{flex:1;min-width:0}
.d-title h3{font-family:"Instrument Serif",Georgia,serif;font-style:italic;font-weight:400;
  font-size:22px;line-height:1.15;overflow-wrap:anywhere}
.d-sec{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);
  display:flex;align-items:center;gap:5px;margin-top:4px}
.d-x{background:none;border:0;font-family:inherit;font-size:14px;cursor:pointer;color:var(--muted)}
.d-cat{font-size:11px;color:var(--blue);cursor:pointer}
.d-cat:hover{text-decoration:underline}
.d-links{display:flex;flex-wrap:wrap;gap:6px}
.d-link{font-size:11px;border:1px solid var(--line-strong);padding:6px 9px;color:var(--ink)}
.d-link:hover{background:#f0f0f0}
.d-link.primary{background:var(--blue);border-color:var(--blue);color:#fff}
.d-h{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);
  border-top:1px solid var(--line);padding-top:12px}
.d-related{display:flex;flex-direction:column;gap:4px}
.d-rel{display:flex;align-items:center;gap:8px;text-align:left;font-family:inherit;font-size:12px;
  background:none;border:1px solid var(--line);padding:6px;cursor:pointer;color:var(--ink)}
.d-rel:hover{background:#f4f4f4}
.d-rel .logo{width:22px;height:22px}
.d-rel span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.d-empty{font-size:11px;color:var(--muted)}
.d-suggest{font-size:11px;color:var(--blue);margin-top:4px}
.d-one{font-size:13px;line-height:1.5;color:var(--ink);font-style:italic}
.d-inf{font-family:var(--mono);font-size:8px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--muted);border:1px solid var(--line);padding:1px 4px;vertical-align:1px}
.d-facts{display:flex;flex-direction:column;gap:6px}
.d-fact{display:flex;gap:10px;font-size:12px;line-height:1.4}
.d-fact .fk{flex:0 0 116px;color:var(--muted);font-family:var(--mono);font-size:10px;
  letter-spacing:.04em;text-transform:uppercase;padding-top:1px}
.d-fact .fv{flex:1;color:var(--ink);overflow-wrap:anywhere}
.d-n{font-family:var(--mono);font-size:10px;color:var(--muted);border:1px solid var(--line);padding:0 5px}
.d-conns{display:flex;flex-direction:column;gap:4px}
.d-conn{display:flex;flex-direction:column;gap:1px;text-align:left;font-family:var(--sans);
  background:none;border:1px solid var(--line);border-left:3px solid var(--blue);
  padding:6px 9px;cursor:pointer;color:var(--ink)}
.d-conn:hover{background:rgba(20,82,255,.06)}
.d-conn .cr{font-family:var(--mono);font-size:9px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.d-conn .cn2{font-size:12px;font-weight:500}
mark{color:#111}
/* accessibility & feel */
:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.pill:active,.sort:active,.hbtn:active,.viewtabs button:active,
.pager button:active,.tile:active,.sbrow:active{transform:translateY(1px)}
.tag{cursor:help;text-decoration:underline dotted;text-underline-offset:2px;text-decoration-thickness:1px}
@media(max-width:900px){
  .sector>.row{min-height:44px}
  .cat{min-height:40px;align-items:center}
  .pill,.sort,.hbtn,.viewtabs button{min-height:40px}
  .pager button{min-height:42px;min-width:44px}
}
/* dark theme */
:root[data-theme=dark]{--bg:#0c0d10;--panel:#15171c;--ink:#e8e8ea;--muted:#9aa1ab;
  --line:#262a31;--line-strong:#3a3f48;--grid:rgba(255,255,255,.035);/*__PALD__*/}
:root[data-theme=dark] .hbtn:hover,:root[data-theme=dark] .d-link:hover,
:root[data-theme=dark] .pill:hover,:root[data-theme=dark] .d-rel:hover,
:root[data-theme=dark] .sort:hover,:root[data-theme=dark] .cat:hover,
:root[data-theme=dark] .pager button:hover:not(:disabled){background:#22252c}
</style>
</head>
<body>
<header>
  <div class="bar">
    <button class="menu-toggle" id="menuToggle" aria-label="Open filters">☰ Filters</button>
    <a class="brand" href="#" id="brandReset" title="Reset all filters">
      <span class="mark"><svg class="ic lmark" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5" stroke-dasharray="8.6 4.7"/><path d="M12 8.5v7M8.5 12h7"/></svg></span>
      <span>
        <h1>The Lithium Index</h1><br>
        <small>Linking the Battery Circular Economy</small>
      </span>
    </a>
    <div class="search">
      <input id="q" type="search" placeholder="Search companies, labs, equipment, services…" autocomplete="off" spellcheck="false" role="combobox" aria-expanded="false" aria-controls="sug">
      <span class="kbd">/</span>
      <div class="sug" id="sug" role="listbox" hidden></div>
    </div>
    <div class="stats">
      <div><b id="statShown">0</b><span>Showing</span></div>
      <div><b id="statCats">__N_CATS__</b><span>Categories</span></div>
      <div><b id="statSecs">__N_SECTORS__</b><span>Sectors</span></div>
    </div>
    <div class="hactions">
      <button class="hbtn" id="submitBtn" title="Submit a company"><svg class="ic" viewBox="0 0 24 24" aria-hidden="true" style="stroke:var(--brand)"><path d="M12 5v14M5 12h14"/></svg>Submit</button>
      <button class="hbtn icon" id="themeBtn" title="Toggle dark mode" aria-label="Toggle dark mode"></button>
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
      <div class="viewtabs" id="viewTabs" role="tablist" aria-label="View">
        <button data-view="landscape" title="Sector overview"><svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>Sectors</button>
        <button data-view="grid" title="Browse all entries"><svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6h13M8 12h13M8 18h13"/><path d="M3 6h.01M3 12h.01M3 18h.01"/></svg>List</button>
        <button data-view="map" title="World map"><svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18 15 15 0 0 1 0-18"/></svg>Map</button>
      </div>
      <div class="pills" id="pills"></div>
      <span class="spacer"></span>
      <select class="sort" id="regionSel" title="Filter by region / country"></select>
      <select class="sort" id="typeSel" title="Filter by type"></select>
      <select class="sort" id="techSel" title="Filter by technology / chemistry"></select>
      <button class="sort" id="sortBtn">Sort: Relevance</button>
    </div>
    <div class="chips" id="chips"></div>
    <div class="crumb" id="crumb" hidden></div>
    <div class="resultline" id="resultLine"></div>
    <div class="landscape" id="landscape"></div>
    <div class="mapwrap" id="map"></div>
    <div class="grid" id="grid"></div>
    <div class="pager" id="pager"></div>
  </main>
</div>

<div class="drawer" id="drawer" hidden>
  <div class="scrim" data-close></div>
  <div class="panel" id="drawerPanel" role="dialog" aria-modal="true"></div>
</div>

<footer>
  <span>The Lithium Index · __N_ENTRIES__ entries · __N_CATS__ categories · __N_SECTORS__ mega-sectors</span>
  <span>linkplus.in — every company is a link · ✓ marks a verified official link; others open a web search</span>
</footer>

<script>
const DB = /*__DATA__*/;
const PER_PAGE = 60;
// Replace with your Google Form / Tally link to collect submissions.
const SUBMIT_URL = "https://docs.google.com/forms/";
const QUICK = ["Cell Manufacturing & OEMs","Materials & Chemicals","Mining & Raw Materials",
  "Recycling & Circular Economy","Manufacturing Equipment","Software, Data & Simulation"];
const I = {
  x:'<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>',
  ext:'<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M9 7h8v8"/></svg>',
  chev:'<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg>',
  sun:'<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
  moon:'<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z"/></svg>',
  batt:'<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="7" width="17" height="10" rx="2"/><path d="M22 10.5v3"/></svg>'
};

const state = {q:"", sector:null, cat:null, stage:null, type:"", tech:"", region:"", country:"", sort:"rel", view:"landscape", page:1};
const STAGE_SECTORS = {}; (DB.stages||[]).forEach(st=>STAGE_SECTORS[st.n]=new Set(st.sectors));
function stageOf(sector){
  for(const st of DB.stages){ if(st.sectors.indexOf(sector)>=0) return st.n; }
  return "";
}
function stageColor(st){ const secs=(STAGE_SECTORS[st]||new Set()); const first=[...secs][0]; return DB.colors[first]||"var(--c1)"; }

const $ = s => document.querySelector(s);
const grid = $("#grid"), pager = $("#pager"), chips = $("#chips"),
      resultLine = $("#resultLine"), treeEl = $("#tree"), pillsEl = $("#pills"),
      crumbEl = $("#crumb"), sugEl = $("#sug"),
      landscapeEl = $("#landscape"), mapEl = $("#map"),
      drawer = $("#drawer"), drawerPanel = $("#drawerPanel");
// Theme applies to #li-root inside a Blogger embed, else the document root.
const ROOT = document.getElementById("li-root") || document.documentElement;

// ---- build sidebar tree ----
function buildTree(){
  let html = "";
  for(const [sector,cats] of Object.entries(DB.tree)){
    const total = cats.reduce((a,c)=>a+c.count,0);
    html += `<div class="sector" data-sector="${esc(sector)}" style="--sc:${DB.colors[sector]||'#0a0a0a'}">
      <div class="row" data-act="sector">
        <span class="nm"><span class="tw">${I.chev}</span>${esc(sector)}</span>
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
  pillsEl.innerHTML = `<button class="pill" data-pill="__all">All</button>` +
    DB.stages.map(st=>`<button class="pill" data-pill="stage:${esc(st.n)}" style="--sc:${stageColor(st.n)}">${esc(st.n)}</button>`).join("");
}
function buildSelects(){
  const typeSel=$("#typeSel"), techSel=$("#techSel");
  typeSel.innerHTML = `<option value="">All types</option>` +
    DB.types.map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join("");
  techSel.innerHTML = `<option value="">All technologies</option>` +
    DB.techs.map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join("");
  const regionSel=$("#regionSel");
  const optGroups = (DB.regions||[]).map(r=>{
    const cs = (DB.countries||[]).filter(c=>entriesRegion(c)===r);
    return `<optgroup label="${esc(r)}"><option value="reg:${esc(r)}">All ${esc(r)}</option>`+
      cs.map(c=>`<option value="co:${esc(c)}">${esc(c)}</option>`).join("")+`</optgroup>`;
  }).join("");
  regionSel.innerHTML = `<option value="">All regions</option>`+optGroups;
}
function entriesRegion(country){
  const e = DB.entries.find(x=>x.co===country);
  return e ? e.rg : "";
}

function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));}

// ---- filtering ----
function filtered(){
  const q = state.q.trim().toLowerCase();
  let rows = DB.entries;
  if(state.cat){ rows = rows.filter(e=>e.c===state.cat); }
  else if(state.sector){ rows = rows.filter(e=>e.s===state.sector); }
  else if(state.stage){ const ss=STAGE_SECTORS[state.stage]||new Set(); rows = rows.filter(e=>ss.has(e.s)); }
  if(state.type){ rows = rows.filter(e=>e.t===state.type); }
  if(state.tech){ rows = rows.filter(e=>e.tech.indexOf(state.tech)>=0); }
  if(state.region){ rows = rows.filter(e=>e.rg===state.region); }
  if(state.country){ rows = rows.filter(e=>e.co===state.country); }
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
function cleanName(name){ return name.replace(/\([^)]*\)/g," ").replace(/\s[-/–]\s.*$/,"").trim(); }
function initials(name){
  const c = cleanName(name).replace(/[^A-Za-z0-9 ]/g," ").trim();
  const w = c.split(/\s+/).filter(Boolean);
  if(!w.length) return "?";
  return (w.length===1 ? w[0].slice(0,2) : w[0][0]+w[1][0]).toUpperCase();
}
function hostOf(u){ try{ return new URL(u).hostname; }catch(_){ return ""; } }
function logoHtml(e){
  // Pinned logo (e.lg) wins; else the domain favicon; else the monogram.
  const h = e.u ? hostOf(e.u) : "";
  const src = e.lg ? e.lg : (h ? `https://www.google.com/s2/favicons?domain=${h}&sz=64` : "");
  const fav = src ? `<img class="fav" loading="lazy" alt="" src="${esc(src)}" onerror="this.remove()">` : "";
  return `<span class="logo" style="--sc:${DB.colors[e.s]||'#0a0a0a'}"><span class="mono">${esc(initials(e.n))}</span>${fav}</span>`;
}

function render(){
  const rows = filtered();
  const q = state.q.trim().toLowerCase();
  $("#statShown").textContent = rows.length.toLocaleString();
  $("#statCats").textContent = new Set(rows.map(e=>e.c)).size;
  $("#statSecs").textContent = new Set(rows.map(e=>e.s)).size;

  const view = state.view;
  landscapeEl.style.display = view==="landscape" ? "" : "none";
  mapEl.style.display       = view==="map"       ? "" : "none";
  grid.style.display        = view==="grid"      ? "" : "none";
  document.querySelectorAll("#viewTabs button").forEach(b=>b.classList.toggle("on", b.dataset.view===view));

  renderChips(); syncSidebar(); renderCrumb();

  if(view==="landscape"){
    renderLandscape();
    resultLine.innerHTML = `<b>${DB.stats.sectors}</b> mega-sectors · <b>${rows.length.toLocaleString()}</b> entries — pick a sector to explore`;
    pager.innerHTML=""; updateHash(); return;
  }
  if(view==="map"){
    renderMap(rows);
    const located = rows.filter(e=>e.co && DB.centroids[e.co]);
    resultLine.innerHTML = `<b>${located.length.toLocaleString()}</b> located entries in <b>${new Set(located.map(e=>e.co)).size}</b> countries — click a bubble to filter`;
    pager.innerHTML=""; updateHash(); return;
  }

  const pages = Math.max(1, Math.ceil(rows.length/PER_PAGE));
  if(state.page>pages) state.page = pages;
  const start = (state.page-1)*PER_PAGE;
  const slice = rows.slice(start, start+PER_PAGE);
  resultLine.innerHTML = rows.length
    ? `Showing <b>${start+1}–${start+slice.length}</b> of <b>${rows.length.toLocaleString()}</b> entries`
    : "";

  if(!rows.length){
    grid.innerHTML = `<div class="empty" style="grid-column:1/-1">
      <svg class="batt-empty" viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="7" width="17" height="10" rx="2"/><path d="M22 10.5v3"/><path d="M5.5 10v4" opacity=".35"/></svg>
      <b>Battery empty — nothing found</b>Try a different term or clear a filter to recharge the list.</div>`;
    pager.innerHTML=""; updateHash(); return;
  }

  grid.innerHTML = slice.map(e=>{
    const verified = !!e.u;
    const href = verified ? e.u : searchUrl(e.n);
    const tags = (e.tech||[]).slice(0,3)
      .map(t=>`<span class="tag" title="${esc(DB.gloss[t]||t)}">${esc(t)}</span>`).join("");
    return `
    <a class="card${verified?" verified":""}" style="--sc:${DB.colors[e.s]||'#0a0a0a'}" href="${href}" target="_blank" rel="noopener" data-id="${e.i}">
      <div class="idx">${logoHtml(e)}<span class="cid">#${e.i}</span><span class="grow"></span>${verified?'<span class="badge">✓ LINK</span>':''}</div>
      <div class="nm">${hl(e.n,q)}</div>
      ${tags?`<div class="tags">${tags}</div>`:""}
      <div class="meta">
        <div class="cat" data-cat="${e.c}">${hl(e.cn,q)}</div>
        <div class="sec"><span class="dot"></span>${esc(e.s)}${e.co?' · '+esc(e.co):''}</div>
      </div>
      <div class="go">${I.ext}${verified?"visit site":"web search"}</div>
    </a>`;}).join("");

  renderPager(pages);
  updateHash();
}

function renderLoop(){
  const W=900, H=470, cx=450, cy=232, r=150;
  const rad=a=>a*Math.PI/180;
  const pt=(a,rr)=>[cx+rr*Math.cos(rad(a)), cy+rr*Math.sin(rad(a))];
  const core=DB.stages.filter(x=>x.k==="core");
  const seg=360/core.length, gap=18, sw=26;
  const cnt=st=>{ const ss=STAGE_SECTORS[st]; let n=0; DB.entries.forEach(e=>{if(ss.has(e.s))n++;}); return n; };
  let arcs="", arrows="", labels="";
  core.forEach((stg,i)=>{
    const a0=-90+i*seg+gap/2, a1=-90+(i+1)*seg-gap/2, mid=(a0+a1)/2;
    const [x0,y0]=pt(a0,r), [x1,y1]=pt(a1,r);
    const col=stageColor(stg.n), n=cnt(stg.n);
    arcs+=`<g class="lp-stage" data-stage="${esc(stg.n)}" tabindex="0" role="button" aria-label="${esc(stg.n)} — ${n} entries">
      <title>${esc(stg.n)} · ${n} entries — click to browse</title>
      <path d="M ${x0.toFixed(1)} ${y0.toFixed(1)} A ${r} ${r} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}"
        fill="none" stroke="transparent" stroke-width="52"/>
      <path d="M ${x0.toFixed(1)} ${y0.toFixed(1)} A ${r} ${r} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}"
        fill="none" stroke="${col}" stroke-width="${sw}"/></g>`;
    const [lx,ly]=pt(mid,r+42);
    const anch=Math.cos(rad(mid))>0.35?"start":(Math.cos(rad(mid))<-0.35?"end":"middle");
    labels+=`<text class="lp-name" x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="${anch}">${i+1}· ${esc(stg.n)}<tspan class="lp-cnt" dx="7">${n}</tspan></text>`;
    // connector arrow at the boundary after this arc (the "link")
    const b=-90+(i+1)*seg;
    const [px,py]=pt(b,r);
    const tx=-Math.sin(rad(b)), ty=Math.cos(rad(b));   // clockwise tangent
    const nx=Math.cos(rad(b)), ny=Math.sin(rad(b));    // radial normal
    const tip=[px+tx*9,py+ty*9], b1=[px-tx*5+nx*7,py-ty*5+ny*7], b2=[px-tx*5-nx*7,py-ty*5-ny*7];
    arrows+=`<g class="lp-link" data-sector="Logistics & Supply Chain" tabindex="0" role="button" aria-label="Logistics and supply chain — the links between stages">
      <title>Logistics &amp; Supply Chain — the links between stages</title>
      <polygon points="${tip.map(v=>v.toFixed(1))} ${b1.map(v=>v.toFixed(1))} ${b2.map(v=>v.toFixed(1))}"/></g>`;
  });
  // brand-red return arc: Recover (mid of last arc) back to Refine (mid of 2nd)
  const aFrom=-90+4*seg+seg/2+8, aTo=-90+seg+seg/2+360-14;
  const r2=r-46;
  const [fx,fy]=pt(aFrom,r2), [tx2,ty2]=pt(aTo,r2);
  const [ex,ey]=pt(aTo,r2);
  const tt=-Math.sin(rad(aTo)), tu=Math.cos(rad(aTo));
  const rn=Math.cos(rad(aTo)), rm=Math.sin(rad(aTo));
  const rtip=[ex+tt*8,ey+tu*8], rb1=[ex-tt*4+rn*5.5,ey-tu*4+rm*5.5], rb2=[ex-tt*4-rn*5.5,ey-tu*4-rm*5.5];
  const ret=`<g class="lp-ret" aria-hidden="true">
    <path d="M ${fx.toFixed(1)} ${fy.toFixed(1)} A ${r2} ${r2} 0 0 1 ${ex.toFixed(1)} ${ey.toFixed(1)}" fill="none"/>
    <polygon points="${rtip.map(v=>v.toFixed(1))} ${rb1.map(v=>v.toFixed(1))} ${rb2.map(v=>v.toFixed(1))}" class="lp-ret-head"/>
    <text class="lp-ret-t" x="${cx}" y="${(cy-r2+30).toFixed(1)}" text-anchor="middle">recovered materials re-enter the loop</text>
  </g>`;
  const center=`<g class="lp-center" aria-hidden="true">
    <circle cx="${cx}" cy="${cy-34}" r="13" class="lp-ring"/>
    <path d="M ${cx} ${cy-39.5} v 11 M ${cx-5.5} ${cy-34} h 11" class="lp-plus"/>
    <text class="lp-center-n" x="${cx}" y="${cy+8}">${DB.stats.entries.toLocaleString()}</text>
    <text class="lp-center-l" x="${cx}" y="${cy+26}">COMPANIES LINKED</text>
    <text class="lp-center-l" x="${cx}" y="${cy+42}">THE BATTERY LOOP</text>
  </g>`;
  // Legend: ALL 12 mega-sectors, grouped by their loop role, every chip the
  // same weight & size — the 5-part circle expands here into its 12 sectors,
  // with Links and Enablers shown at equal prominence (no longer demoted).
  const secCount=sec=>{let n=0;DB.entries.forEach(e=>{if(e.s===sec)n++;});return n;};
  let ci=0;
  const groups=DB.stages.map(st=>{
    const num = st.k==="core" ? (++ci)+"· " : "";
    const roleAttr = st.k==="core" ? `data-stage="${esc(st.n)}"`
                   : (st.k==="links" ? `data-sector="${esc(st.sectors[0])}"` : "");
    const chips=st.sectors.map(sec=>`<button class="ll-sec" data-sector="${esc(sec)}" style="--sc:${DB.colors[sec]||'var(--c1)'}"><span class="dot"></span><span class="ll-nm">${esc(sec)}</span><span class="ll-ct">${secCount(sec)}</span></button>`).join("");
    return `<div class="ll-group ll-${st.k}"><div class="ll-role" ${roleAttr}>${num}${esc(st.n)}</div><div class="ll-secs">${chips}</div></div>`;
  }).join("");
  const legend=`<div class="loop-legend"><div class="ll-h">All 12 mega-sectors — every company is a link in the loop</div><div class="ll-groups">${groups}</div></div>`;
  const flow = `<g class="lp-flow" aria-hidden="true"><circle r="5" cx="${cx}" cy="${(cy-r).toFixed(1)}" class="lp-flow-dot"/></g>`;
  return `<div class="loop">
    <svg viewBox="0 0 ${W} ${H}" class="loopsvg" role="img" aria-label="The battery circular economy loop">
      ${arcs}${arrows}${ret}${flow}${labels}${center}
    </svg>${legend}</div>`;
}

function renderLandscape(){
  const st = DB.stats;
  const kpis = `<div class="kpis">
    <div class="kpi"><b>${st.entries.toLocaleString()}</b><span>Entries</span></div>
    <div class="kpi"><b>${st.categories}</b><span>Categories</span></div>
    <div class="kpi"><b>${(DB.countries||[]).length}</b><span>Countries</span></div>
    <div class="kpi"><b>${st.withUrl}</b><span>Verified links</span></div>
  </div>`;
  const rows = Object.entries(DB.tree)
    .map(([sec,cats])=>({sec, n:cats.reduce((a,c)=>a+c.count,0)}))
    .sort((a,b)=>b.n-a.n);
  const max = rows[0].n;
  const chart = `<div class="secbar"><div class="secbar-h">Entries per mega-sector — click to browse</div>` +
    rows.map(r=>`<button class="sbrow" data-sector="${esc(r.sec)}" title="Browse ${esc(r.sec)}">
      <span class="sbn">${esc(r.sec)}</span>
      <span class="sbtrack"><span class="sbfill" style="width:${(100*r.n/max).toFixed(1)}%;background:${DB.colors[r.sec]||'var(--c1)'}"></span></span>
      <span class="sbv">${r.n}</span></button>`).join("") + `</div>`;
  const tiles = Object.entries(DB.tree).map(([sec,cats])=>{
    const total = cats.reduce((a,c)=>a+c.count,0);
    const top = cats.slice().sort((a,b)=>b.count-a.count).slice(0,4).map(c=>esc(c.name)).join(" · ");
    return `<button class="tile" data-sector="${esc(sec)}" style="--sc:${DB.colors[sec]||'#0a0a0a'}">
      <div class="tile-h"><span class="tile-n">${esc(sec)}</span><span class="tile-c">${total}</span></div>
      <div class="tile-sub">${cats.length} categories</div>
      <div class="tile-top">${top}</div>
    </button>`;
  }).join("");
  landscapeEl.innerHTML = renderLoop() + kpis + chart + `<div class="tiles">` + tiles + `</div>`;
}

function renderMap(rows){
  const W=1000, H=500;
  const proj=(lat,lon)=>[(lon+180)/360*W, (90-lat)/180*H];
  const byC={};
  rows.forEach(e=>{ if(e.co && DB.centroids[e.co]) (byC[e.co]=byC[e.co]||[]).push(e); });
  const maxN = Math.max(1, ...Object.values(byC).map(a=>a.length));
  let grat="";
  for(let lon=-150;lon<=150;lon+=30){ const x=(lon+180)/360*W; grat+=`<line class="grat" x1="${x}" y1="0" x2="${x}" y2="${H}"/>`; }
  for(let lat=-60;lat<=60;lat+=30){ const y=(90-lat)/180*H; grat+=`<line class="grat" x1="0" y1="${y}" x2="${W}" y2="${y}"/>`; }
  const guides=[["NORTH AMERICA",45,-100],["SOUTH AMERICA",-15,-60],["EUROPE",54,15],
                ["AFRICA",5,20],["ASIA",46,90],["OCEANIA",-25,140]]
    .map(([t,lat,lon])=>{const[x,y]=proj(lat,lon);return `<text class="guide" x="${x.toFixed(0)}" y="${y.toFixed(0)}">${t}</text>`;}).join("");
  const bubbles = Object.entries(byC).sort((a,b)=>b[1].length-a[1].length).map(([co,arr])=>{
    const [lat,lon]=DB.centroids[co]; const [x,y]=proj(lat,lon);
    const r = 6 + 30*Math.sqrt(arr.length/maxN);
    const cnt={}; arr.forEach(e=>cnt[e.s]=(cnt[e.s]||0)+1);
    const dom = Object.entries(cnt).sort((a,b)=>b[1]-a[1])[0][0];
    const col = DB.colors[dom] || "#2563eb";
    const on = state.country===co;
    return `<g class="bub${on?' on':''}" data-co="${esc(co)}" transform="translate(${x.toFixed(1)},${y.toFixed(1)})" tabindex="0">
      <circle r="${r.toFixed(1)}" fill="${col}" fill-opacity="${on?0.85:0.5}" stroke="${col}" stroke-width="1.5"/>
      <text class="bub-n" y="${(-r-4).toFixed(1)}">${esc(co)} · ${arr.length}</text>
    </g>`;
  }).join("");
  mapEl.innerHTML = `<svg viewBox="0 0 ${W} ${H}" class="worldmap" preserveAspectRatio="xMidYMid meet" role="img" aria-label="World map of battery entries by country">
    <rect class="ocean" x="0" y="0" width="${W}" height="${H}"/>${grat}${guides}${bubbles}
  </svg>`;
}

function openDetail(e){
  const cn = cleanName(e.n) || e.n;
  const site = e.u ? ["Official site", e.u, true] : null;
  const links = [
    site,
    ["Google", "https://www.google.com/search?q="+encodeURIComponent(cn)],
    ["LinkedIn", "https://www.google.com/search?q="+encodeURIComponent(cn+" site:linkedin.com/company")],
    ["News", "https://news.google.com/search?q="+encodeURIComponent(cn+" battery")],
    ["Patents", "https://patents.google.com/?q="+encodeURIComponent(cn)],
  ].filter(Boolean);
  const tags = (e.tech||[]).map(t=>`<span class="tag" title="${esc(DB.gloss[t]||t)}">${esc(t)}</span>`).join("");
  const related = DB.entries.filter(x=>x.c===e.c && x.i!==e.i).slice(0,8);
  drawerPanel.innerHTML = `
    <div class="d-top">
      ${logoHtml(e)}
      <div class="d-title"><h3>${esc(e.n)}</h3>
        <div class="d-sec"><span class="dot" style="--sc:${DB.colors[e.s]||'#0a0a0a'}"></span>${esc(e.et||"")} · ${esc(e.s)}${e.co?' · '+esc(e.co):''} · Loop: ${esc(stageOf(e.s))}</div>
      </div>
      <button class="d-x" data-close aria-label="Close">${I.x}</button>
    </div>
    ${entityProfile(e)}
    ${connectionsHtml(e)}
    ${tags?`<div class="d-h">Technology</div><div class="tags d-tags">${tags}</div>`:""}
    <div class="d-h">Actions</div>
    <div class="d-links">
      ${links.map(([label,url,primary])=>`<a class="d-link${primary?' primary':''}" href="${url}" target="_blank" rel="noopener">${esc(label)} ${I.ext}</a>`).join("")}
    </div>
    <div class="d-h">Related in ${esc(e.cn)}</div>
    <div class="d-related">
      ${related.length?related.map(r=>`<button class="d-rel" data-id="${r.i}">${logoHtml(r)}<span>${esc(r.n)}</span></button>`).join(""):'<span class="d-empty">No other entries in this category.</span>'}
    </div>
    <a class="d-suggest" href="${SUBMIT_URL}" target="_blank" rel="noopener">✎ Suggest an edit or add a link</a>`;
  drawer.hidden = false;
  requestAnimationFrame(()=>drawer.classList.add("open"));
}
const REL_LABELS = {SUPPLIES_TO:"supplies", SUPPLIES_EQUIPMENT_TO:"supplies equipment",
  EXPORTS_THROUGH:"exports through", USES_SOFTWARE:"uses", INVESTED_IN:"invested in",
  SUBSIDIARY_OF:"subsidiary of", PARTNER_OF:"partner", JV_WITH:"joint venture",
  RECYCLES_FOR:"recycles for", COMPETES_WITH:"competes with", FOUNDER_OF:"founder of",
  FORMER_EMPLOYER:"formerly at", LEADS:"leads", MEMBER_OF:"member of", COVERS:"covers"};
const PROFILE_ROWS = [
  ["status","Status"],["ownership","Ownership"],["founded","Founded"],["ticker","Ticker"],
  ["product","Core product / material"],["chemistry","Chemistry"],["form_factor","Form factor"],
  ["deployment","Deployment"],["target","Target market"],["key_ip","Key IP"],["extraction","Extraction"],
  ["facility_type","Facility type"],["capacity","Capacity"],["hazmat","Hazmat handling"],["strategic_role","Strategic role"],
  ["institution_type","Institution type"],["funding_source","Funding source"],["notable_facility","Facility"],
  ["title","Role"],["expertise","Expertise"],["esg","ESG"],["media_type","Format"]];
function entityProfile(e){
  const m = e.m || {};
  const rows = [];
  const status = m.status || e.stt;
  if(status && status!=="Active") rows.push(["Status", esc(status)]);
  for(const [k,label] of PROFILE_ROWS){
    if(k==="status") continue;
    if(m[k]!=null && m[k]!=="") rows.push([label, esc(String(m[k]))]);
  }
  const seeded = !!e.m;
  const oneline = (e.one) ? `<div class="d-one">${esc(e.one)}${e.ov||seeded?"":' <span class="d-inf" title="auto-inferred from the entry name">inferred</span>'}</div>` : "";
  if(!rows.length) return oneline;
  return oneline + `<div class="d-h">Profile${seeded?"":' <span class="d-inf">inferred</span>'}</div>
    <div class="d-facts">${rows.map(([k,v])=>`<div class="d-fact"><span class="fk">${esc(k)}</span><span class="fv">${v}</span></div>`).join("")}</div>`;
}
function connectionsHtml(e){
  const list = (DB.rels||{})[e.eid] || [];
  if(!list.length) return "";
  const items = list.map(r=>{
    const lbl = REL_LABELS[r.r] || r.r.toLowerCase().replace(/_/g," ");
    const arrow = r.d==="out" ? "→" : "←";
    return `<button class="d-conn" data-eid="${esc(r.e)}">
        <span class="cr">${arrow} ${esc(lbl)}</span><span class="cn2">${esc(r.n)}</span></button>`;
  }).join("");
  return `<div class="d-h">Connections <span class="d-n">${list.length}</span></div><div class="d-conns">${items}</div>`;
}
function openByEid(eid){ const e = DB.entries.find(x=>x.eid===eid); if(e) openDetail(e); }
function closeDrawer(){ drawer.classList.remove("open"); setTimeout(()=>{drawer.hidden=true;}, 200); }

function renderCrumb(){
  if(state.view!=="grid" || (!state.sector && !state.cat)){ crumbEl.hidden=true; return; }
  const parts = [`<a data-crumb="all">All sectors</a>`];
  if(state.sector) parts.push(state.cat
    ? `<a data-crumb="sector">${esc(state.sector)}</a>` : `<b>${esc(state.sector)}</b>`);
  if(state.cat){
    const name=(DB.entries.find(e=>e.c===state.cat)||{}).cn||("#"+state.cat);
    parts.push(`<b>${esc(name)}</b>`);
  }
  crumbEl.innerHTML = parts.join('<span class="sep">▸</span>');
  crumbEl.hidden=false;
}

function renderChips(){
  const c = [];
  if(state.stage) c.push(`<span class="chip"><b>Stage:</b> ${esc(state.stage)} <span class="x" data-clear="stage">${I.x}</span></span>`);
  if(state.sector) c.push(`<span class="chip"><b>Sector:</b> ${esc(state.sector)} <span class="x" data-clear="sector">${I.x}</span></span>`);
  if(state.cat){
    const name = (DB.entries.find(e=>e.c===state.cat)||{}).cn || ("#"+state.cat);
    c.push(`<span class="chip"><b>Category:</b> ${esc(name)} <span class="x" data-clear="cat">${I.x}</span></span>`);
  }
  if(state.type) c.push(`<span class="chip"><b>Type:</b> ${esc(state.type)} <span class="x" data-clear="type">${I.x}</span></span>`);
  if(state.tech) c.push(`<span class="chip"><b>Tech:</b> ${esc(state.tech)} <span class="x" data-clear="tech">${I.x}</span></span>`);
  if(state.region) c.push(`<span class="chip"><b>Region:</b> ${esc(state.region)} <span class="x" data-clear="region">${I.x}</span></span>`);
  if(state.country) c.push(`<span class="chip"><b>Country:</b> ${esc(state.country)} <span class="x" data-clear="country">${I.x}</span></span>`);
  if(state.q.trim()) c.push(`<span class="chip"><b>Search:</b> "${esc(state.q.trim())}" <span class="x" data-clear="q">${I.x}</span></span>`);
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
    p.classList.toggle("on", v==="__all" ? (!state.sector&&!state.cat&&!state.stage) : v==="stage:"+state.stage);
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
function setSector(s){ state.sector=s; state.cat=null; state.stage=null; state.page=1; if(s) state.view="grid"; render(); if(s) scrollToSelectedSector(); }
function setStage(st){ state.stage=st; state.sector=null; state.cat=null; state.page=1; state.view="grid"; render(); flashResults(); }
function setCat(id){
  const e = DB.entries.find(e=>e.c===id);
  state.cat=id; state.sector=e?e.s:state.sector; state.stage=null; state.page=1; state.view="grid"; render(); flashResults();
}
function setView(v){ state.view=v; state.page=1; render(); }

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
  if(v==="__all"){ state.stage=null; setSector(null); return; }
  const st=v.slice(6);
  if(state.stage===st){ state.stage=null; state.page=1; render(); }
  else setStage(st);
});
chips.addEventListener("click", ev=>{
  const x = ev.target.closest("[data-clear]"); if(!x) return;
  const k=x.dataset.clear;
  if(k==="sector") state.sector=null;
  if(k==="cat") state.cat=null;
  if(k==="stage") state.stage=null;
  if(k==="type"){ state.type=""; $("#typeSel").value=""; }
  if(k==="tech"){ state.tech=""; $("#techSel").value=""; }
  if(k==="region"){ state.region=""; $("#regionSel").value=""; }
  if(k==="country"){ state.country=""; $("#regionSel").value=""; }
  if(k==="q"){ state.q=""; $("#q").value=""; }
  state.page=1; render();
});
grid.addEventListener("click", ev=>{
  const cat = ev.target.closest(".cat[data-cat]");
  if(cat){ ev.preventDefault(); ev.stopPropagation(); setCat(Number(cat.dataset.cat)); return; }
  const card = ev.target.closest(".card");
  if(card){ ev.preventDefault(); const e = DB.entries.find(x=>x.i===Number(card.dataset.id)); if(e) openDetail(e); }
});
landscapeEl.addEventListener("click", ev=>{
  const stg = ev.target.closest("[data-stage]");
  if(stg){ setStage(stg.dataset.stage); return; }
  const t = ev.target.closest("[data-sector]"); if(!t) return;
  setSector(t.dataset.sector);
});
mapEl.addEventListener("click", ev=>{
  const g = ev.target.closest(".bub"); if(!g) return;
  const co = g.dataset.co;
  state.country = state.country===co ? "" : co;
  $("#regionSel").value = state.country ? "co:"+state.country : "";
  state.view="grid"; state.page=1; render(); flashResults();
});
$("#viewTabs").addEventListener("click", ev=>{
  const b = ev.target.closest("button[data-view]"); if(!b) return;
  setView(b.dataset.view);
});
drawer.addEventListener("click", ev=>{
  if(ev.target.closest("[data-close]")){ closeDrawer(); return; }
  const conn = ev.target.closest(".d-conn[data-eid]");
  if(conn){ drawerPanel.scrollTop=0; openByEid(conn.dataset.eid); return; }
  const rel = ev.target.closest(".d-rel");
  if(rel){ const e=DB.entries.find(x=>x.i===Number(rel.dataset.id)); if(e){ drawerPanel.scrollTop=0; openDetail(e); } return; }
  const cat = ev.target.closest(".d-cat[data-cat]");
  if(cat){ closeDrawer(); setCat(Number(cat.dataset.cat)); }
});
$("#submitBtn").addEventListener("click", ()=>window.open(SUBMIT_URL, "_blank", "noopener"));
crumbEl.addEventListener("click", ev=>{
  const a=ev.target.closest("[data-crumb]"); if(!a) return;
  if(a.dataset.crumb==="all"){ state.sector=null; state.cat=null; state.page=1; state.view="landscape"; render(); }
  else { setSector(state.sector); }
});

// ---- search autocomplete ----
let sugIdx=-1, sugItems=[];
function buildSug(q){
  q=q.trim().toLowerCase();
  if(q.length<2){ hideSug(); return; }
  const cats=[]; const seen=new Set();
  for(const [sec,cs] of Object.entries(DB.tree)){
    for(const c of cs){ if(c.name.toLowerCase().includes(q) && !seen.has(c.id)){ seen.add(c.id); cats.push({t:"cat",id:c.id,n:c.name,cnt:c.count}); if(cats.length>=4) break; } }
    if(cats.length>=4) break;
  }
  const cos=[];
  for(const e of DB.entries){ if(e.n.toLowerCase().includes(q)){ cos.push({t:"co",id:e.i,n:e.n}); if(cos.length>=8-cats.length) break; } }
  sugItems=[...cats,...cos]; sugIdx=-1;
  if(!sugItems.length){ hideSug(); return; }
  sugEl.innerHTML=sugItems.map((it,i)=>`<button data-i="${i}" role="option">
      <span class="k${it.t==="cat"?" kc":""}">${it.t==="cat"?"CAT":"CO"}</span>
      <span class="sn">${hl(it.n,q)}</span>${it.cnt?`<span class="cnt">${it.cnt}</span>`:""}
    </button>`).join("");
  sugEl.hidden=false; $("#q").setAttribute("aria-expanded","true");
}
function hideSug(){ sugEl.hidden=true; sugIdx=-1; $("#q").setAttribute("aria-expanded","false"); }
function pickSug(i){
  const it=sugItems[i]; if(!it) return;
  hideSug();
  if(it.t==="cat"){ state.q=""; $("#q").value=""; setCat(it.id); }
  else { const e=DB.entries.find(x=>x.i===it.id); if(e) openDetail(e); }
}
sugEl.addEventListener("mousedown", ev=>{
  const b=ev.target.closest("button[data-i]"); if(!b) return;
  ev.preventDefault(); pickSug(Number(b.dataset.i));
});
$("#q").addEventListener("keydown", ev=>{
  if(sugEl.hidden) return;
  if(ev.key==="ArrowDown"||ev.key==="ArrowUp"){
    ev.preventDefault();
    sugIdx=(sugIdx+(ev.key==="ArrowDown"?1:-1)+sugItems.length)%sugItems.length;
    sugEl.querySelectorAll("button").forEach((b,i)=>b.classList.toggle("on",i===sugIdx));
  } else if(ev.key==="Enter" && sugIdx>=0){ ev.preventDefault(); pickSug(sugIdx); }
  else if(ev.key==="Escape"){ hideSug(); }
});
$("#q").addEventListener("blur", ()=>setTimeout(hideSug,150));
pager.addEventListener("click", ev=>{
  const b=ev.target.closest("button[data-page]"); if(!b||b.disabled) return;
  state.page=Number(b.dataset.page); window.scrollTo({top:0,behavior:"smooth"}); render();
});

let t=null;
$("#q").addEventListener("input", e=>{
  clearTimeout(t);
  t=setTimeout(()=>{ state.q=e.target.value; state.page=1; if(state.q.trim()&&state.view!=="grid") state.view="grid"; render(); buildSug(e.target.value); }, 140);
});
document.addEventListener("keydown", e=>{
  if(e.key==="/" && document.activeElement!==$("#q")){ e.preventDefault(); $("#q").focus(); }
  if(e.key==="Escape"){ if(!drawer.hidden){ closeDrawer(); } else { $("#q").blur(); } }
});

$("#typeSel").addEventListener("change", e=>{ state.type=e.target.value; state.page=1; state.view="grid"; render(); });
$("#techSel").addEventListener("change", e=>{ state.tech=e.target.value; state.page=1; state.view="grid"; render(); });
$("#regionSel").addEventListener("change", e=>{
  const v=e.target.value;
  state.region = v.startsWith("reg:") ? v.slice(4) : "";
  state.country = v.startsWith("co:") ? v.slice(3) : "";
  state.page=1; state.view="grid"; render();
});

const SORTS=[["rel","Relevance"],["az","A → Z"],["za","Z → A"]];
$("#sortBtn").addEventListener("click", ()=>{
  const i=SORTS.findIndex(s=>s[0]===state.sort);
  const next=SORTS[(i+1)%SORTS.length];
  state.sort=next[0]; $("#sortBtn").textContent="Sort: "+next[1]; render();
});

$("#clearNav").addEventListener("click", resetAll);
$("#brandReset").addEventListener("click", e=>{e.preventDefault();resetAll();});
function resetAll(){ Object.assign(state,{q:"",sector:null,cat:null,stage:null,type:"",tech:"",region:"",country:"",page:1,view:"landscape"});
  $("#q").value=""; $("#typeSel").value=""; $("#techSel").value=""; $("#regionSel").value="";
  document.querySelectorAll(".sector.open").forEach(s=>s.classList.remove("open")); render(); }

// ---- dark mode ----
function applyTheme(mode){ ROOT.setAttribute("data-theme", mode); $("#themeBtn").innerHTML = mode==="dark"?I.sun:I.moon; }
(function initTheme(){
  let saved=null; try{ saved=localStorage.getItem("li-theme"); }catch(_){}
  const mode = saved || (matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark":"light");
  applyTheme(mode);
})();
$("#themeBtn").addEventListener("click", ()=>{
  const mode = ROOT.getAttribute("data-theme")==="dark"?"light":"dark";
  applyTheme(mode); try{ localStorage.setItem("li-theme", mode); }catch(_){}
});

// ---- shareable URL (location hash) ----
let hashLock=false;
function updateHash(){
  if(hashLock) return;
  const p=new URLSearchParams();
  if(state.view!=="landscape") p.set("v",state.view);
  if(state.sector) p.set("sec",state.sector);
  if(state.stage) p.set("st",state.stage);
  if(state.cat) p.set("cat",state.cat);
  if(state.type) p.set("t",state.type);
  if(state.tech) p.set("tech",state.tech);
  if(state.region) p.set("rg",state.region);
  if(state.country) p.set("co",state.country);
  if(state.q.trim()) p.set("q",state.q.trim());
  if(state.page>1) p.set("pg",state.page);
  const h=p.toString();
  try{ history.replaceState(null,"", h?("#"+h):location.pathname+location.search); }catch(_){}
}
function applyHash(){
  const h=location.hash.replace(/^#/,""); if(!h) return;
  const p=new URLSearchParams(h);
  state.view = p.get("v")||"landscape";
  state.sector = p.get("sec")||null;
  state.stage = p.get("st")||null;
  state.cat = p.get("cat")?Number(p.get("cat")):null;
  state.type = p.get("t")||"";
  state.tech = p.get("tech")||"";
  state.region = p.get("rg")||"";
  state.country = p.get("co")||"";
  state.q = p.get("q")||"";
  state.page = p.get("pg")?Number(p.get("pg")):1;
  $("#q").value=state.q; $("#typeSel").value=state.type; $("#techSel").value=state.tech;
  $("#regionSel").value = state.country?("co:"+state.country):(state.region?("reg:"+state.region):"");
  const si=SORTS.findIndex(s=>s[0]===state.sort); if(si>=0)$("#sortBtn").textContent="Sort: "+SORTS[si][1];
}
window.addEventListener("hashchange", ()=>{ hashLock=true; applyHash(); render(); hashLock=false; });

// mobile nav
const body=document.body;
$("#menuToggle").addEventListener("click",()=>body.classList.toggle("nav-open"));
function closeNav(){body.classList.remove("nav-open");}
document.addEventListener("click",e=>{
  if(body.classList.contains("nav-open") && !e.target.closest("aside") && !e.target.closest("#menuToggle"))
    closeNav();
});

buildTree(); buildPills(); buildSelects();
hashLock=true; applyHash(); hashLock=false;
render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
