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
- **Quick-filter pills** for the most-used sectors.
- **Active-filter chips** (sector / category / search) with one-click clear.
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

## Adding real URLs

The source list contained company **names only**, so each card currently links
to a web search for the entry. To attach verified URLs, extend the entry format
in `data/companies.txt` (e.g. `1. CATL | https://www.catl.com`) and teach
`build.py` to parse the trailing URL, then re-run the build.

## Suggested next steps

- Enrich entries with real URLs, HQ country, and technology tags (NMC / LFP /
  solid-state) to power additional facet filters.
- Add a "Submit a company" form (Tally / Google Form embed) for crowdsourcing.
- Optional dark-mode toggle and a "Sponsored Pin" slot per category.
