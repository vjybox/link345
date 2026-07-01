# The Lithium Index

A futuristic-minimalist **homepage / directory** of the lithium-ion battery
industry — **2,129 entries** across **150 categories** grouped into
**20 color-coded mega-sectors** (incl. **100+ gigafactories** in 25 countries),
built as a single self-contained `index.html` with no runtime dependencies
(all data is embedded, zero external API calls).

## Live features

- **Three views** via a toggle: a **Sector landscape** market-map home (20
  colored tiles), a **List** of entry cards, and a self-contained **world Map**
  of plants/companies (bubbles by country, no map library).
- **Full-text search** across name, category and sector — debounced, `/`
  shortcut, match highlighting. Header stats update live with the result set.
- **Sidebar tree**: 20 mega-sectors → 150 categories with live counts;
  color-coded per sector.
- **Filters** (all AND-combine, shown as clearable chips): **Type** (18),
  **Technology/chemistry** (12, auto-detected), and **Region/Country**
  (grouped by region).
- **Company detail drawer** — click a card for a slide-in profile with smart
  research links (Official site · Google · LinkedIn · News · Patents) and
  related companies in the same category.
- **Logos** on every card (favicon of the verified domain, with a colored
  monogram fallback). 315 entries link to their official website (✓ badge).
- **Dark mode** toggle (remembers your choice; follows system by default).
- **Shareable URLs** — the current view/filters/search are encoded in the
  page hash, so any filtered state can be bookmarked or linked.
- **Submit a company** button + per-entry "suggest an edit" link
  (set `SUBMIT_URL` in `build.py` to your Google Form / Tally).
- Quick-filter pills, Relevance/A→Z/Z→A sort, 60/page pagination, responsive.
- **Design**: light + dark, 48px grid, per-sector accent colors, gradient
  header strip, JetBrains Mono body + Instrument Serif italic headings.

Verified in-browser: landscape 20 tiles · Recycling sector → 80 · drill-down
Recycling & Second Life → 20 · "tesla" → 5 · map 215 located entries in 25
countries · drawer + dark mode + hash deep-links all working.

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
