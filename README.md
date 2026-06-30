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
| `index.html` | The deployable single-file homepage (build output). |
| `build.py` | Parses the dataset, assigns mega-sectors, renders `index.html`. |
| `data/companies.txt` | Source dataset — `## id \| Category` headers + numbered entries. |
| `data/directory.json` | Generated structured data (also embedded in the HTML). |

## Build

```bash
python3 build.py
```

No third-party packages required (standard library only). The script prints a
warning if any category is left without a mega-sector.

## Deploy to Google Blogger

`index.html` is fully self-contained, so any of these work:

1. **Page / Post (easiest).** New Page → switch to **HTML view** → paste the
   entire contents of `index.html`. Some Blogger sanitizers strip `<style>`/
   `<script>`; if so, use option 2.
2. **Custom theme (pixel-perfect).** Theme → Edit HTML → replace the whole
   template with `index.html`. The directory then *is* your blog homepage.
3. **HTML/JavaScript gadget.** Layout → Add a Gadget → HTML/JavaScript → paste
   `index.html`. Good for embedding inside an existing theme.

Any static host (GitHub Pages, Netlify, Cloudflare Pages, S3) also works —
just serve `index.html`.

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
