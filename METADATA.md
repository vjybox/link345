# Entity Metadata & Relationships (Phase 1)

Turns the directory from a list into an **entity-graph**: every entry has a
stable ID and (optionally) a rich profile + typed connections to other
entries. Surfaced in the detail drawer as **Profile** + **Connections**
(click a connection to jump to that entity — the "living supply-chain map").

## Files you edit
- **`data/metadata/*.json`** — curated profiles, sharded one file per sector,
  keyed by a *cleaned name token* (matches an entry whose cleaned name equals
  the key or starts with `"<key> "`, e.g. `"catl"`, `"port of rotterdam"`,
  `"jb straubel"`). Hand-seeded records are shown as verified; every other
  entry gets auto-derived base fields (`type` / `status` / `one_liner`)
  flagged **inferred**. All shards are glob-merged at build time.
- **`data/relationships.json`** — directed edges `["source","RELATION","target"]`
  using the same keys. Unmatched keys are skipped with a build warning.

Re-run `python3 build.py` after editing; it prints how many records/edges
matched, and warns (with the exact key) on anything unmatched.

⚠️ **Key uniqueness for entities with same-named siblings** (e.g. a company
that also has its own gigafactory/plant line elsewhere in the dataset): the
metadata key must be a genuine prefix of the intended entry's *cleaned* name,
and `resolve()` picks the **shortest** matching entry for a given key. A short
key like `"acme"` can silently attach to a shorter same-company plant entry
("Acme — Ohio") instead of the corporate line ("Acme Corporation"). When in
doubt, use the full cleaned name as the key for an exact match.

## Base fields (any entity)
`type` (Corporate·Facility·People·Research·Institution·Media) · `status`
(Active·Announced·Under-Construction·Acquired·Defunct) · `ownership` ·
`founded` · `one_liner` · `about` (optional full paragraph override) ·
`parent` · plus auto: id, sector, loop stage, tech tags. **HQ location**:
`country=`/`city=` live directly on the `data/companies.txt` line (not in
metadata) — see below.

## Type-specific fields
- **Corporate:** `ticker · product · chemistry · form_factor · deployment · target · key_ip · extraction · esg · production_base`
- **Facility:** `facility_type · capacity · hazmat · city · strategic_role`
- **People:** `title · employer · prev_employer[] · expertise`
- **Research:** `institution_type · funding_source · notable_facility`
- **Media:** `media_type`

`city` in metadata is a *plant's own* location (Facility type only — e.g. a
gigafactory entry). `production_base` on a **Corporate** entity is a short
freeform string for where it manufactures, when that's *not* already covered
by a separate Facility entry in the dataset — e.g.
`"Greenbushes & Kemerton, Australia"`. Don't duplicate: if the company's
plants are already individual gigafactory entries, skip `production_base` and
rely on those instead.

## HQ location (country + city)
Every `data/companies.txt` line can carry `| country=<Country> | city=<City>`.
`country` already exists and drives the region facet + map; `city` is
optional and, when present, upgrades the entry page's location line from
just "Country" to "City, Country". See
[`data/LOCATION_PROMPT.md`](data/LOCATION_PROMPT.md) for the bulk
enrichment workflow (HQ + production base, cross-checked across multiple AI
tools) and `tools/apply_locations.py` for merging the result.

## Relations
`SUPPLIES_TO · SUPPLIES_EQUIPMENT_TO · EXPORTS_THROUGH · USES_SOFTWARE ·
INVESTED_IN · SUBSIDIARY_OF · PARTNER_OF · JV_WITH · RECYCLES_FOR ·
COMPETES_WITH · FOUNDER_OF · FORMER_EMPLOYER · LEADS · MEMBER_OF · COVERS`

## Roadmap
- **P1 (done):** IDs for all 1,632 · Profile + Connections drawer + graph
  traversal · sharded metadata · 327 seeded profiles, 92 edges, 102
  gigafactory Facility profiles, free local-LLM "About" enrichment.
- **P1.5 (in progress):** HQ country/city + production base for every entry.
- **P2:** facet filters (ownership/chemistry/status/founded) + capacity roll-ups
  + a data-completeness meter.
- **P3:** in-drawer ego-graph + scenario queries.
- **P4:** crowdsource intake via the Submit form.
