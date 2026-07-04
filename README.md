# The Lithium Index

A futuristic-minimalist **homepage / directory** of the lithium-ion battery
industry — **1,632 curated entries** across **30 categories** grouped into
**12 Loop-aligned mega-sectors** (incl. **100+ gigafactories** in 27 countries),
built as a single self-contained `index.html` with no runtime dependencies
(all data is embedded, zero external API calls).

## Live features

- **Three views** via a toggle: a **Sector landscape** market-map home (12
  colored tiles + The Loop hero), a **List** of entry cards, and a self-contained **world Map**
  of plants/companies (bubbles by country, no map library).
- **Full-text search** across name, category and sector — debounced, `/`
  shortcut, match highlighting. Header stats update live with the result set.
- **Sidebar tree**: 12 mega-sectors → 30 categories with live counts;
  color-coded per sector.
- **Filters** (all AND-combine, shown as clearable chips): **Type** (18),
  **Technology/chemistry** (12, auto-detected), and **Region/Country**
  (grouped by region).
- **Entity intelligence drawer** — click any card for a profile (status,
  ownership, founded, chemistry, form factor, capacity…), a **Connections**
  graph (supplies / exports-through / subsidiary-of / invested-in… — click a
  connection to jump to that entity), smart research links, and related
  companies. Schema + how to contribute: [`METADATA.md`](METADATA.md).
- **Logos** on every card (favicon of the verified domain, with a colored
  monogram fallback). 214 entries link to their official website (✓ badge).
- **Dark mode** toggle (remembers your choice; follows system by default).
- **Shareable URLs** — the current view/filters/search are encoded in the
  page hash, so any filtered state can be bookmarked or linked.
- **Submit a company** button + per-entry "suggest an edit" link
  (set `SUBMIT_URL` in `build.py` to your Google Form / Tally).
- Quick-filter pills, Relevance/A→Z/Z→A sort, 60/page pagination, responsive.
- **Design**: light + dark, 48px grid, per-sector accent colors, gradient
  header strip, JetBrains Mono body + Instrument Serif italic headings.

Verified in-browser: landscape 12 tiles + The Loop · Recycling sector → 52 ·
"tesla" → 10 · map 242 located entries in 27 countries · Loop stage filters ·
drawer + dark mode + hash deep-links all working.

## Files

| Path | Purpose |
| --- | --- |
| `index.html` | Standalone full-page app (search/filters/pagination) — for static hosting / GitHub Pages. |
| `blogger-page.html` | **No-JS directory that works pasted into a Blogger Page** (native `<details>`; no scripts/forms). |
| `blogger-embed.html` | Scoped app for an HTML/JavaScript **gadget** — no `<head>`/`<body>`, container-query layout. |
| `build.py` | Parses the dataset, assigns mega-sectors, renders all three HTML files + JSON. |
| `data/companies.txt` | Source dataset — `## id \| Category` headers + numbered entries (optional `\| url \| country= \| logo=`). |
| `data/metadata/*.json` | Curated entity profiles, sharded one file per sector (glob-merged at build). |
| `data/relationships.json` | Directed graph edges between entities (the Connections drawer). |
| `data/ENRICHMENT_PROMPT.md` | Copy-paste AI prompt to populate/enrich the three data files at scale. |
| `dist/directory.json` | Generated structured data (also embedded in the HTML) — git-ignored build artifact. |
| `dist/e/<slug>.html` | One generated **content page per entry** (profile, supply-chain network, discovery lists) — git-ignored. |
| `dist/{s,c,country,t,stage}/` | ~90 generated **hub/list pages** (sectors, categories, countries, technologies, loop stages). |
| `dist/lists.html` + `dist/sitemap.xml` | The "Explore all lists" index and a sitemap of all ~1,720 URLs. |
| `dist/blogger-import.xml` | Blogger export: **import once** to create one post per entry — git-ignored. |
| `tools/legacy/` | One-time migration sources (`_source_v2.txt`, `_gigafactories.txt`) for `tools/migrate_v2.py`. |

## Build

```bash
python3 build.py
```

No third-party packages required (standard library only). The script prints a
warning if any category is left without a mega-sector.

## Deploy to Google Blogger

**Important:** Blogger *Pages* strip `<script>`/`<input>`/`<select>`/`<button>`,
so pasting the *interactive* app into a Page yields an empty styled box.
Three working routes are documented in
**[`BLOGGER-SETUP.md`](BLOGGER-SETUP.md)**:

1. **Paste `blogger-page.html` into a Page (no hosting, works instantly).**
   A no-JavaScript build using native `<details>` — full browsable catalog,
   counts, verified links, tech tags, jump nav. No live search box/filters
   (those need JS; use Ctrl/⌘-F, or route 2).
2. **iframe the full app:** host `index.html` on GitHub Pages, embed it with a
   one-line `<iframe>` in your Page — restores live search, filters, pagination.
3. **HTML/JavaScript gadget:** paste `blogger-embed.html` into a
   Layout → HTML/JavaScript gadget (gadgets allow scripts, unlike Pages).

For static hosting (GitHub Pages / Netlify / Cloudflare Pages / S3), serve
`index.html`.

## Adding / overriding URLs

214 well-known, unambiguous brands already resolve to verified official
domains via the curated `KNOWN_URLS` map in `build.py`; everything else links
to a web search. Two ways to add more:

1. **Per-entry override (highest priority).** Append pipe-separated fields to
   any line in `data/companies.txt` — a URL, `country=`, and/or `logo=`:
   `1. CATL (…) | https://www.catl.com | country=China | logo=https://…/catl.svg`
   The card logo prefers `logo=`, then the domain favicon, then a monogram.
2. **Curated map.** Add `"<cleaned name>": "https://…"` to `KNOWN_URLS`.
   An entry matches when its cleaned name (parentheticals/notes stripped,
   lowercased) equals the key or begins with `"<key> "`.

Re-run `python3 build.py` after either change.

## Enriching entity metadata

Profiles and relationships live in `data/metadata/*.json` (sharded per sector)
and `data/relationships.json`. To populate them at scale, paste
[`data/ENRICHMENT_PROMPT.md`](data/ENRICHMENT_PROMPT.md) into any AI with one
category's entries; drop its three output blocks into the files and re-run
`python3 build.py` (it reports matched records/edges and warns on bad keys).

## Per-entry content pages (free, no API)

`python3 build.py` also generates **one content page per entry** — a profile,
key facts (sector-aware), a written "About" paragraph, the connections graph,
and research links — with **no API and no cost**: it's pure templating over the
data you already have. The prose is composed deterministically from the
metadata. To upgrade it to genuinely written paragraphs for **free, with no API
key**, run a **local** model over every entry:

```bash
# one-time: install Ollama (ollama.com), then
ollama pull llama3.2
python3 build.py                        # refresh dist/directory.json
python3 tools/enrich_about.py --model llama3.2   # writes data/about.json
python3 build.py                        # rebuild pages with the paragraphs
```

`tools/enrich_about.py` talks to the local Ollama endpoint (stdlib only, no
packages), resumes automatically, and saves after every entry. It writes
`data/about.json` (keyed by entry id), which `build.py` merges into the pages
and the Blogger XML — overriding the composed text. `--seeded-only`,
`--sector "…"`, and `--limit N` scope a run. You can also hand-write the same
`about` field via `ENRICHMENT_PROMPT.md` and a free chat tier. Two zero-cost
ways to publish all ~1,632 pages:

1. **Static hosting** — deploy the whole `dist/` folder as-is to GitHub Pages /
   Netlify / Cloudflare Pages (all free); it's a complete site: the app as
   `index.html`, ~1,632 entry pages, ~90 hub/list pages (per sector, category,
   country, technology and loop stage), an `lists.html` explore index and a
   `sitemap.xml`. Every fact on an entry page links into a list and every list
   links back (~40k verified internal links), and each page ships a meta
   description + JSON-LD (Organization/Person, BreadcrumbList, ItemList).
   Set `SITE_BASE` in `build.py` to your deployed URL for absolute links in the
   sitemap and Blogger XML.
2. **Blogger import** — upload `dist/blogger-import.xml` via Blogger →
   Settings → *Import content*. Creates one post per entry, labeled by
   mega-sector + category, so they're browsable inside your existing blog. No
   external host. (Internal cross-links become absolute if `SITE_BASE` is set,
   otherwise they degrade to plain text — never broken links.)

(`dist/` is git-ignored — regenerate and deploy it; the repo stays lean.)

## Taking it forward

The full launch / content-ops / growth playbook — hosting, Blogger import,
Search Console, the weekly enrichment flywheel, and the upgrade roadmap —
lives in **[`NEXT-STEPS.md`](NEXT-STEPS.md)**.

## Suggested next steps

- Enrich entries with real URLs, HQ country, and technology tags (NMC / LFP /
  solid-state) to power additional facet filters.
- Add a "Submit a company" form (Tally / Google Form embed) for crowdsourcing.
- Optional dark-mode toggle and a "Sponsored Pin" slot per category.
