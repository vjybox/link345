# Entity Metadata & Relationships (Phase 1)

Turns the directory from a list into an **entity-graph**: every entry has a
stable ID and (optionally) a rich profile + typed connections to other
entries. Surfaced in the detail drawer as **Profile** + **Connections**
(click a connection to jump to that entity — the "living supply-chain map").

## Files you edit
- **`data/metadata.json`** — curated profiles, keyed by a *cleaned name token*
  (matches an entry whose cleaned name equals the key or starts with `"<key> "`,
  e.g. `"catl"`, `"port of rotterdam"`, `"jb straubel"`). Hand-seeded records are
  shown as verified; every other entry gets auto-derived base fields
  (`type` / `status` / `one_liner`) flagged **inferred**.
- **`data/relationships.json`** — directed edges `["source","RELATION","target"]`
  using the same keys. Unmatched keys are skipped with a build warning.

Re-run `python3 build.py` after editing; it prints how many records/edges matched.

## Base fields (any entity)
`type` (Corporate·Facility·People·Research·Institution·Media) · `status`
(Active·Announced·Under-Construction·Acquired·Defunct) · `ownership` ·
`founded` · `one_liner` · `parent` · plus auto: id, sector, loop stage, HQ
country, url, tech tags.

## Type-specific fields
- **Corporate:** `ticker · product · chemistry · form_factor · deployment · target · key_ip · extraction · esg`
- **Facility:** `facility_type · capacity · hazmat · city · strategic_role`
- **People:** `title · employer · prev_employer[] · expertise`
- **Research:** `institution_type · funding_source · notable_facility`
- **Media:** `media_type`

## Relations
`SUPPLIES_TO · SUPPLIES_EQUIPMENT_TO · EXPORTS_THROUGH · USES_SOFTWARE ·
INVESTED_IN · SUBSIDIARY_OF · PARTNER_OF · JV_WITH · RECYCLES_FOR ·
COMPETES_WITH · FOUNDER_OF · FORMER_EMPLOYER · LEADS · MEMBER_OF · COVERS`

## Roadmap
- **P1 (done):** IDs for all 1,632 · ~50-entity seed · 61 edges · Profile +
  Connections drawer + graph traversal.
- **P2:** facet filters (ownership/chemistry/status/founded) + capacity roll-ups
  + a data-completeness meter.
- **P3:** in-drawer ego-graph + scenario queries.
- **P4:** LLM-assisted enrichment + crowdsource intake via the Submit form.
