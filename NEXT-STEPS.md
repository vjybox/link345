# Taking The Lithium Index forward

Everything is built: the interactive app, the Blogger builds, 1,632 entry
pages + 88 hub pages + `lists.html` + `sitemap.xml` (all generated into
`dist/`), and the free enrichment pipeline. This is the playbook for
launching it, growing the content, and what to build next.

> **Windows users:** the shell snippets below are bash. Run them in **Git
> Bash** (installed alongside Git for Windows — right-click a folder →
> "Git Bash Here") or WSL, not plain PowerShell — commands like `rm -rf`,
> `cp -r`, and `&&` chaining don't work the same way there. `python3
> build.py` and `python3 tools/enrich_about.py` work fine directly in
> PowerShell; it's only the multi-command deploy scripts that need bash.

**Two constants to set in `build.py` before launch** (both currently
placeholders):

| Constant | Where | Set it to |
| --- | --- | --- |
| `SITE_BASE` | `build.py` (search `SITE_BASE = ""`) | Your deployed URL, e.g. `https://<user>.github.io/link345` — unlocks a valid sitemap, BreadcrumbList JSON-LD, and absolute cross-links in the Blogger XML. The build prints a `[warn]` until you do. |
| `SUBMIT_URL` | `build.py` (search `const SUBMIT_URL`) | Your Google Form / Tally URL for "Submit a company". |

---

## Phase 0 — Ship it (one sitting, ~1–2 hours)

1. **Merge the branch.** Merge `claude/lithium-index-directory-n9a7c0` into
   `main` so main is the source of truth.

2. **Host the full site — GitHub Pages (free, recommended).**
   `dist/` is a complete standalone site (app at `index.html`, entry pages,
   hubs, sitemap). Simplest manual flow:

   ```bash
   # after setting SITE_BASE:
   python3 build.py
   # publish dist/ to a gh-pages branch (one-liner with git worktree):
   git worktree add ../gh-pages gh-pages 2>/dev/null || git worktree add -b gh-pages ../gh-pages
   rm -rf ../gh-pages/* && cp -r dist/* ../gh-pages/
   cd ../gh-pages && git add -A && git commit -m "deploy" && git push -u origin gh-pages
   ```

   Then repo → Settings → Pages → deploy from `gh-pages` branch. (Later this
   can become a GitHub Action that rebuilds on every push.)
   Optional: point a subdomain like `index.linkplus.in` at Pages (CNAME) and
   use that as `SITE_BASE`.

3. **Wire Blogger (linkplus.in)** — see [`BLOGGER-SETUP.md`](BLOGGER-SETUP.md):
   - a Page with an `<iframe>` of the hosted `index.html` (full app), and/or
     paste `blogger-page.html` into a Page (no-JS catalog);
   - optionally import `dist/blogger-import.xml` once (Settings → Manage blog
     → Import content) → 1,632 posts labeled by sector + category.

4. **Create the Submit form** (Google Forms or Tally, free). Suggested
   fields: company name · official URL · country · category (dropdown of the
   30) · what they do (1–2 sentences) · related companies + relationship ·
   submitter email. Paste its URL into `SUBMIT_URL`, rebuild, redeploy.

5. **Google Search Console**: verify the domain, submit
   `<SITE_BASE>/sitemap.xml` (1,722 URLs). Hub pages ("battery recycling
   companies", "gigafactories in Germany") are the expected organic winners;
   indexing ramps over weeks.

6. **Analytics (free)**: GoatCounter or Cloudflare Web Analytics — a single
   script tag to add to the page shell when you've picked one.

---

## Phase 1 — The content flywheel (~2–4 h/week — this is the moat)

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

**Priorities, in order:**
1. The ~150 most-connected "spine" companies (they appear on many pages).
2. All 102 gigafactory entries (capacity / chemistry / customer) — the plant
   atlas is a genuine differentiator.
3. **Relationship edges** — highest leverage per line: every edge enriches
   two entity pages plus the "two steps away" blocks. Target: 61 → 500+.

---

## Phase 2 — Product upgrades (build work, roughly one session each)

Ranked by value; each can be requested as its own task:

1. **Metadata facet filters + completeness meter** — filter by ownership /
   chemistry / form-factor / status; per-sector "profiled N of M" progress.
   Makes every Phase-1 batch immediately visible and useful.
2. **Ego-graph** — a small interactive network (1–2 hops) in the drawer and
   on entry pages; same inline-SVG approach as the Loop and the map.
3. **Submissions intake tool** — `tools/import_submissions.py` to parse the
   Submit form's response CSV into ready-to-review entries/metadata with
   dedup, closing the crowdsourcing loop.
4. **Analytics content** — "Most connected" leaderboards per sector; a
   supply-chain path finder ("how is Pilbara linked to Tesla?").
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
