# Data Enrichment Prompt

Paste the block below into any capable AI, then append **one category's raw
entries** (20–40 lines) where indicated. The AI returns three fenced blocks
that drop straight into the build files with no reformatting:

- ` ```companies ` → lines for `data/companies.txt`
- ` ```metadata ` → an object to merge into a `data/metadata/<sector>.json` shard
- ` ```relationships ` → edges to append to `data/relationships.json` → `edges`

After pasting the output into the files, run `python3 build.py`. It prints how
many records and edges matched and warns on any unmatched key, so mistakes
surface immediately.

---

````text
You are enriching a directory of the lithium-ion battery industry. I will give you
a BATCH of raw entries (one industry category at a time). For each entry, return
structured data in THREE fenced blocks that match my build pipeline exactly. Do
not invent facts — see the ACCURACY RULES. Output only the three blocks.

────────────────────────────────────────────────────────
KEY RULE (critical — this is how records get matched to entries)
────────────────────────────────────────────────────────
Every metadata record and every relationship uses a "cleaned-name key":
  • lowercase
  • drop anything in parentheses and any " - note" / " / note" suffix
  • collapse whitespace
Examples:  "CATL (Contemporary Amperex…)" → "catl"
           "JB Straubel"                  → "jb straubel"
           "Port of Rotterdam"            → "port of rotterdam"
A record matches an entry when the entry's cleaned name EQUALS the key or
STARTS WITH "<key> ". Keep keys short and unambiguous (use "catl", not
"contemporary amperex technology"). Reuse the SAME key everywhere.

────────────────────────────────────────────────────────
BLOCK 1 — URLs & country  (feeds data/companies.txt)
────────────────────────────────────────────────────────
For each entry that has an official website and/or a headquarters country,
return a line in this exact format (fields optional but keep the order):

  <original entry name> | <https official url> | country=<Country> | logo=<https logo url>

Rules:
  • Use the REAL official homepage, https, no tracking params, no trailing slash.
  • country = HQ country, full English name (e.g. "South Korea", "United States").
  • logo= is OPTIONAL — only add it when the site's favicon is wrong/ugly and you
    know a clean official logo URL (SVG/PNG). Omit it otherwise; the site falls
    back to the domain favicon automatically.
  • If you don't know the URL, omit the "| https…" part entirely — never guess.

────────────────────────────────────────────────────────
BLOCK 2 — profiles  (feeds data/metadata/<sector>.json)
────────────────────────────────────────────────────────
Return a JSON object keyed by cleaned-name key. Only include entries you can
describe from real knowledge. Use ONLY these fields.

BASE (any entity):
  type      one of: Corporate | Facility | People | Research | Institution | Media
  status    one of: Active | Announced | Under-Construction | Acquired | Defunct
  ownership e.g. "Public" | "Private" | "Private (VC)" | "Subsidiary" | "State-owned"
  founded   integer year
  one_liner ≤ 90 chars, factual, no marketing fluff
  about     OPTIONAL 2–4 sentence factual paragraph; overrides the auto-composed
            prose on the entry's content page. Omit to keep the templated text.
  parent    cleaned-name key of parent company (if a subsidiary)

TYPE-SPECIFIC (add only the ones that apply):
  Corporate:   ticker · product · chemistry · form_factor · deployment · target · key_ip · extraction · esg
  Facility:    facility_type · capacity · hazmat · city · strategic_role
  People:      title · employer(key) · prev_employer([keys]) · expertise
  Research:    institution_type · funding_source · notable_facility
  Media:       media_type

Field notes:
  chemistry   e.g. "LFP, NMC", "NCA", "Solid-state", "Na-ion", "Silicon anode"
  form_factor e.g. "Prismatic", "Pouch", "Cylindrical (4680)"
  ticker      "EXCHANGE: SYMBOL" e.g. "NASDAQ: TSLA"
  employer / prev_employer / parent  → use cleaned-name KEYS, not display names

────────────────────────────────────────────────────────
BLOCK 3 — relationships  (feeds data/relationships.json → "edges")
────────────────────────────────────────────────────────
Return a JSON array of directed edges ["source_key", "RELATION", "target_key"]
using cleaned-name keys. Only include relationships you are confident are real
and public. Use ONLY these relations:

  SUPPLIES_TO            (raw material / component / cell supplier → customer)
  SUPPLIES_EQUIPMENT_TO  (machinery/tooling maker → factory)
  EXPORTS_THROUGH        (company → port/logistics hub)
  USES_SOFTWARE          (operator → software vendor)
  INVESTED_IN            (investor → startup)
  SUBSIDIARY_OF          (child → parent)
  PARTNER_OF · JV_WITH · RECYCLES_FOR · COMPETES_WITH
  FOUNDER_OF (person→company) · FORMER_EMPLOYER (person→company)
  LEADS (person→company) · MEMBER_OF (→ alliance/body) · COVERS (media→subject)

Direction matters: ["albemarle","SUPPLIES_TO","catl"] means Albemarle supplies CATL.

────────────────────────────────────────────────────────
ACCURACY RULES (read carefully)
────────────────────────────────────────────────────────
  • Never fabricate a URL, ticker, founding year, capacity, or relationship.
  • If unsure of a value, OMIT the field. Omission is always better than a guess.
  • Prefer widely-reported, durable facts over recent/volatile ones.
  • If a whole entry is unknown to you, skip it (don't emit an empty record).
  • Keep one_liner neutral and specific ("Korean pouch-cell maker; Ford JV"),
    not promotional ("world-leading innovative solutions provider").

────────────────────────────────────────────────────────
WORKED EXAMPLE (input → output)
────────────────────────────────────────────────────────
INPUT batch:
  1. CATL (Contemporary Amperex Technology Co., Limited)
  2. Redwood Materials
  3. JB Straubel

OUTPUT:

```companies
CATL (Contemporary Amperex Technology Co., Limited) | https://www.catl.com | country=China
Redwood Materials | https://www.redwoodmaterials.com | country=United States
```

```metadata
{
  "catl": {"type":"Corporate","status":"Active","ownership":"Public","ticker":"SZSE: 300750","founded":2011,"one_liner":"World's largest EV & ESS battery maker.","product":"Li-ion cells, EV packs, ESS","chemistry":"LFP, NMC, Na-ion","form_factor":"Prismatic","key_ip":"Cell-to-Pack (CTP), Shenxing"},
  "redwood materials": {"type":"Corporate","status":"Active","ownership":"Private (VC)","founded":2017,"one_liner":"Closed-loop recycler + cathode/anode-foil maker.","product":"Recycled cathode & copper foil"},
  "jb straubel": {"type":"People","status":"Active","one_liner":"Ex-Tesla CTO; founder & CEO of Redwood Materials.","title":"Founder & CEO, Redwood Materials","employer":"redwood materials","prev_employer":["tesla"],"expertise":"Pack architecture, recycling"}
}
```

```relationships
[
  ["catl","SUPPLIES_TO","tesla"],
  ["jb straubel","FOUNDER_OF","redwood materials"],
  ["jb straubel","FORMER_EMPLOYER","tesla"]
]
```

────────────────────────────────────────────────────────
Now process THIS batch (category: <PASTE CATEGORY NAME>):
<PASTE 20–40 RAW ENTRY LINES HERE>
````

---

## Where the output goes

| Block | File | How |
| --- | --- | --- |
| `companies` | `data/companies.txt` | Replace the matching numbered lines (keep the `N.` prefix) with the enriched versions. |
| `metadata` | `data/metadata/<sector>.json` | Merge the object into the shard for that sector (one file per category/sector). |
| `relationships` | `data/relationships.json` | Append the edges into the `edges` array. |

`build.py` globs every `data/metadata/*.json` shard (plus a legacy top-level
`data/metadata.json` if present) and merges them, so you can enrich one sector
per file without touching the others.
