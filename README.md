# The Lithium Index

A futuristic-minimalist **homepage / directory** of the lithium-ion battery
industry — **1,996 entries** across **146 categories** grouped into
**20 mega-sectors**, built as a single self-contained `index.html` with no
runtime dependencies (all data is embedded, zero external API calls).

## Live features

- **Full-text search** across name, category and sector — debounced, with a
  `/` keyboard shortcut and match highlighting.
- **Sidebar navigation tree**: 20 mega-sectors → drill down to any of the
  146 categories, each with a live entry count.
- **Type filter** (18 values: Manufacturer/OEM, Materials, Mining, Equipment,
  Software, Testing, Logistics, Finance, Consulting, …).
- **Technology / chemistry filter** (Solid-State, LFP, NMC/NCA, Sodium-ion,
  Silicon Anode, Lithium-Metal, Graphene, Supercapacitor, Cathode, Anode,
  Electrolyte, Separator) — all detected deterministically from entry text.
- **Verified links**: 269 marquee entries link to their official website
  (marked with a ✓ badge); the rest fall back to a web search.
- **Quick-filter pills** for the most-used sectors.
- **Active-filter chips** (sector / category / type / tech / search) with
  one-click clear. All filters combine (AND).
- **Sort**: Relevance · A→Z · Z→A.
- **Pagination** at 60 entries per page.
- **Responsive** — collapsible filter drawer on mobile.
- **Design**: light mode, 48px grid, sharp 1px borders, JetBrains Mono body +
  Instrument Serif italic headings, electric-blue / hot-orange accents.

Verified: Recycling & Circular Economy sector → 80 · Recycling & Second Life
category → 20 · "tesla" search → 5.

## Files

| Path | Purpose |
| --- | --- |
| `index.html` | Standalone full-page app (search/filters/pagination) — for static hosting / GitHub Pages. |
| `blogger-page.html` | **No-JS directory that works pasted into a Blogger Page** (native `<details>`; no scripts/forms). |
| `blogger-embed.html` | Scoped app for an HTML/JavaScript **gadget** — no `<head>`/`<body>`, container-query layout. |
| `build.py` | Parses the dataset, assigns mega-sectors, renders all three HTML files + JSON. |
| `data/companies.txt` | Source dataset — `## id \| Category` headers + numbered entries. |
| `data/directory.json` | Generated structured data (also embedded in the HTML). |

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

269 well-known, unambiguous brands already resolve to verified official
domains via the curated `KNOWN_URLS` map in `build.py`; everything else links
to a web search. Two ways to add more:

1. **Per-entry override (highest priority).** Append a URL to any line in
   `data/companies.txt`:
   `1. CATL (Contemporary Amperex Technology Co., Limited) | https://www.catl.com`
2. **Curated map.** Add `"<cleaned name>": "https://…"` to `KNOWN_URLS`.
   An entry matches when its cleaned name (parentheticals/notes stripped,
   lowercased) equals the key or begins with `"<key> "`.

Re-run `python3 build.py` after either change.

## Suggested next steps

- Enrich entries with real URLs, HQ country, and technology tags (NMC / LFP /
  solid-state) to power additional facet filters.
- Add a "Submit a company" form (Tally / Google Form embed) for crowdsourcing.
- Optional dark-mode toggle and a "Sponsored Pin" slot per category.
