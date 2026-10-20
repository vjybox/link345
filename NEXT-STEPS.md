# Taking The Lithium Index forward

Everything is built: the interactive app, the Blogger builds, 1,632 entry
pages + 88 hub pages + `lists.html` + `sitemap.xml` (all generated into
`dist/`), and the free enrichment pipeline. This is the playbook for
launching it, growing the content, and what to build next.

> **Windows users:** the shell snippets below are bash. Easiest fix: run them
> in **Git Bash** (installed alongside Git for Windows — right-click a
> folder → "Git Bash Here") or WSL, where they work as written. `python3
> build.py` and `python3 tools/enrich_about.py` work fine directly in
> PowerShell either way — it's only the multi-command lines that need bash.
>
> If you're staying in plain **Windows PowerShell** (the blue one, version
> 5.1 — not `pwsh`/PowerShell 7), translate as you go:
>
> | This guide writes (bash) | Windows PowerShell 5.1 |
> | --- | --- |
> | `cmd1 && cmd2` | `cmd1; cmd2` — or just put each on its own line/Enter |
> | `open file.html` | `ii file.html` (or `start file.html`) |
> | `rm -rf dir` | `Remove-Item -Recurse -Force dir` |
> | `cp -r src dst` | `Copy-Item -Recurse src dst` |
> | `grep -c pattern file` | `python3 -c "import json; print(len(json.load(open('file'))) - 1)"` for JSON key counts |
>
> Note `;` in PowerShell always runs the next command even if the first
> failed (unlike bash's `&&`), so for anything that must stop on error
> (like `git commit && git push`), run each command on its own line and
> check the output before continuing.

**Two constants to set in `build.py` before launch:**

| Constant | Where | Set it to |
| --- | --- | --- |
| `SITE_BASE` | `build.py` (search `SITE_BASE = ""`) | Your deployed URL, e.g. `https://yourdomain.com` — unlocks a valid sitemap, BreadcrumbList JSON-LD, and absolute cross-links in the Blogger XML. The build prints a `[warn]` until you do. |
| `SUBMIT_URL` | `build.py` (search `const SUBMIT_URL`) | **Already set** to `submit.html` — the self-hosted form below. No action needed unless you want something else. |

---

## Phase 0 — Ship it (self-hosted on Synology/Docker)

Hosting choice: **self-hosted via Docker on your own Synology NAS**, with
your own SQLite database for submissions and analytics — no GitHub Pages,
no Google Forms, no third-party analytics. Full walkthrough:
[`DEPLOY-SYNOLOGY.md`](DEPLOY-SYNOLOGY.md). Short version:

1. **Merge the branch** — done; `main` is now the source of truth.

2. **Get the repo + `dist/` onto the NAS**, `cp .env.example .env` and set
   a real `ADMIN_PASSWORD`, then `python3 build.py && docker compose up -d --build`.
   This brings up two containers: `web` (nginx serving `dist/`, reverse-
   proxying `/api/*`) and `api` (Flask + SQLite — `server/app.py`).

3. **Submit a company** is now a native page (`submit.html`), posting to
   your own `/api/submit` — no Google Form to create. Review submissions
   and export them as CSV at `/admin` (Basic Auth: `ADMIN_USER`/
   `ADMIN_PASSWORD`), then turn reviewed rows into real entries with
   `python3 tools/import_submissions.py <csv>` (dedups against existing
   entries, flags anything ambiguous for manual review instead of guessing).

4. **Analytics** is already wired — every page beacons a pageview to your
   own `/api/pageview` (no cookies, no third party). View counts at `/admin`.

5. **Wire Blogger (linkplus.in)** — see [`BLOGGER-SETUP.md`](BLOGGER-SETUP.md):
   - a Page with an `<iframe>` of your hosted `index.html` (full app),
     and/or paste `blogger-page.html` into a Page (no-JS catalog);
   - optionally import `dist/blogger-import.xml` once (Settings → Manage blog
     → Import content) → 1,632 posts labeled by sector + category.

6. **Google Search Console**: verify the domain, submit
   `<SITE_BASE>/sitemap.xml` (1,728 URLs). Hub pages ("battery recycling
   companies", "gigafactories in Germany") are the expected organic winners;
   indexing ramps over weeks.

---


## Phase 1 — The content flywheel (~2–4 h/week — this is the moat)

> Using more than one AI tool (e.g. ChatGPT alongside Claude) to generate or
> cross-check this content? Read [`MULTI-AI-WORKFLOW.md`](MULTI-AI-WORKFLOW.md)
> first — it's short and prevents the two ways this has gone wrong before
> (format drift, and one AI silently "revising" another's work).

Work **one sector per week**, two batches each:

**Facts batch** (any free AI chat):
1. Paste [`data/ENRICHMENT_PROMPT.md`](data/ENRICHMENT_PROMPT.md) + 20–40
   entries of one category.
2. Drop the three output blocks into `data/companies.txt`, the sector's
   `data/metadata/*.json` shard, and `data/relationships.json`.
3. `python3 build.py` — it reports matched records/edges and warns on bad keys.

**Prose batch** (your machine, free local LLM):
```bash
ollama pull llama3.2                                   # once
python3 tools/enrich_about.py --model llama3.2 --seeded-only   # first run
python3 tools/enrich_about.py --model llama3.2 --sector "Cells & Chemistry"
python3 build.py                                       # merge into pages
```
QA ~5 pages in `dist/e/` per batch (watch for invented numbers), commit
`data/about.json`, redeploy.

**HQ location + production base** (any AI tool, cross-checked): see
[`data/LOCATION_PROMPT.md`](data/LOCATION_PROMPT.md) for the prompt and
[`tools/apply_locations.py`](tools/apply_locations.py) for merging the
cross-checked result. Every entry gains a "City, Country" HQ line; Corporate
entries can also get a `production_base` (where they actually manufacture,
when that's not already one of the 102 gigafactory plant entries).

**Priorities, in order:**
1. ~~The ~150 most-connected "spine" companies~~ — done.
2. ~~All 102 gigafactory entries~~ — done (Facility profiles in
   `data/metadata/14-gigafactories.json`).
3. **HQ + production base for every entry** — in progress; start with the
   already-profiled 327 entities (`data/LOCATION_PROMPT.md`), then the rest.
4. **Relationship edges** — highest leverage per line: every edge enriches
   two entity pages plus the "two steps away" blocks, the ego-graph, and
   the path finder/leaderboards. Target: 185 → 500+ (92 → 149 → 185 done in
   Batches C/D; 127 entities now have at least one connection). Next: more
   equipment-maker and BMS/power-electronics pairs, deeper recycling
   partnerships, and more OEM↔startup investment ties.

---

## Phase 2 — Product upgrades (build work, roughly one session each)

Ranked by value; each can be requested as its own task:

1. ~~**Metadata facet filters + completeness meter**~~ — done: "More
   filters" (Ownership/Chemistry/Form factor/Status) in the toolbar, a
   "Profiled" KPI tile, and a per-sector completeness bar on every
   landscape tile.
2. **Ego-graph** — a small interactive network (1–2 hops) in the drawer and
   on entry pages; same inline-SVG approach as the Loop and the map.
3. ~~**Submissions intake tool**~~ — done:
   [`tools/import_submissions.py`](tools/import_submissions.py) parses the
   self-hosted Submit form's CSV export into ready-to-merge entries/metadata
   with dedup, closing the crowdsourcing loop end-to-end (self-hosted form →
   admin review → import → build).
4. ~~**Analytics content**~~ — done: every sector hub page (`dist/s/*.html`)
   has a "Most connected" top-10; the header's **Path finder** button
   answers "how is Pilbara linked to Tesla?" with the actual shortest chain
   (BFS over the relationship graph, capped at 5 hops, click any entity in
   the chain to open it). Pageview leaderboards from the self-hosted
   SQLite data (`/admin`) are still open if useful later.
5. **Monetization scaffolding** (once traffic justifies): sponsored pin per
   category, Claimed/Verified badge tier, newsletter signup embed.

---

## Phase 3 — Distribution (ongoing)

- Share **hub pages** (they are ready-made "Top X" lists) and the **Loop**
  visual on LinkedIn / battery communities — the Loop is the brand asset.
- Answer "who supplies whom" questions anywhere with entry-page links.
- Watch Search Console monthly: enrich first the entries of whichever hubs
  start ranking — compounding wins.

## Weekly rhythm (suggested)

| When | What |
| --- | --- |
| Weekly | 1 facts batch + 1 prose batch (Phase 1), redeploy |
| Weekly | Share 1 hub page or insight (Phase 3) |
| Monthly | Check Search Console + analytics; pick the next Phase 2 upgrade |
