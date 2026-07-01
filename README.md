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
| `index.html` | Standalone full-page homepage (use for static hosting / GitHub Pages). |
| `blogger-embed.html` | **Paste-into-Blogger build** — scoped, no `<head>`/`<body>`, container-query layout. |
| `build.py` | Parses the dataset, assigns mega-sectors, renders both HTML files + JSON. |
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
so pasting the app into a Page yields an empty styled box — a Blogger Page
cannot run JavaScript. Use one of the working routes in
**[`BLOGGER-SETUP.md`](BLOGGER-SETUP.md)**:

1. **Recommended — iframe:** host `index.html` on GitHub Pages and embed it
   with a one-line `<iframe>` in your Blogger Page. Scripts run on the host;
   the Page just frames it. Full steps in `BLOGGER-SETUP.md`.
2. **HTML/JavaScript gadget:** paste `blogger-embed.html` into a
   Layout → HTML/JavaScript gadget (gadgets allow scripts, unlike Pages).

`blogger-embed.html` is the scoped, `@import`-font, container-query build made
for embedding inside a theme; `index.html` is the standalone full page used
for hosting (GitHub Pages / Netlify / Cloudflare Pages / S3).

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
