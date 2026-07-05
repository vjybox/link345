# HQ Location & Production Base — Enrichment Prompt

Paste the block below into any AI tool along with a batch of company names
(20–40 at a time, one category at a time works well). Run the **same batch
through 2–3 different AI tools**, compare the answers, and keep only the
facts that agree (or that you can verify yourself) — that's the
cross-checking step. Paste the final, reconciled answer into a plain text
file in the **exact pipe format** shown below, then merge it with
[`tools/apply_locations.py`](../tools/apply_locations.py).

---

## The prompt

````text
For each company below, give its headquarters location and, if different,
where it actually manufactures/produces. Output ONE LINE PER COMPANY in
EXACTLY this pipe-delimited format, nothing else (no numbering, no
markdown, no extra commentary):

Company Name | HQ City | HQ Country | Production base(s)

Rules:
- HQ City / HQ Country = where the company is legally headquartered.
- Production base(s) = the actual manufacturing/production site(s), ONLY
  if they differ meaningfully from HQ or there are multiple important ones.
  Format multiple sites as "City1 (Country1); City2 (Country2)". If
  production happens at/near HQ, or you don't know, leave this column BLANK
  — do not guess or repeat the HQ as filler.
- If you don't know the HQ city or country confidently, leave that column
  BLANK rather than guessing. Do not fabricate a location.
- Use the company's real, current, publicly known headquarters — not a
  historical one, unless the company has since relocated (then use current).
- Keep city/country names in plain English (e.g. "South Korea" not "Korea,
  Republic of").
- Output nothing but the pipe-delimited lines (one per company). No header
  row, no blank lines between entries, no explanation before or after.

Companies:
<PASTE 20–40 NAMES HERE, ONE PER LINE>
````

## Worked example

Input companies:
```
CATL
Albemarle
Redwood Materials
```

Expected output:
```
CATL | Ningde | China | Ningde, Yibin & Liyang (China); Debrecen (Hungary); Arnstadt (Germany)
Albemarle | Charlotte | United States | Kings Mountain, NC & Silver Peak, NV (USA); Salar de Atacama (Chile); Greenbushes JV (Australia)
Redwood Materials | Carson City | United States |
```
(Redwood's production base is left blank since its main campus *is* near
its Carson City / Storey County, Nevada HQ — no separate distant site to
call out.)

## Cross-checking workflow

1. Pick a batch of 20–40 company names from one sector/category.
2. Run the prompt above through 2–3 AI tools (e.g. Claude, ChatGPT, Gemini).
3. Compare the outputs line by line. Where they agree, keep it. Where they
   disagree or one is blank, spot-check with a web search rather than
   guessing which AI to trust.
4. Save the final, reconciled lines into a text file, e.g.
   `data/locations-batch1.txt` (a header row `Company Name | HQ City | HQ
   Country | Production base(s)` is fine — the merge script skips it).
5. Merge it in:
   ```bash
   python3 build.py                                  # refresh dist/directory.json
   python3 tools/apply_locations.py data/locations-batch1.txt
   python3 build.py                                  # apply + check for [warn] lines
   ```
   The script reports how many rows resolved and writes any unmatched
   company names to `data/locations-batch1.misses.txt` for you to review
   (usually a naming mismatch — try the fuller/shorter form of the name).
6. Spot-check a few `dist/e/<slug>.html` pages to confirm the HQ line and
   "Production base(s)" row look right, then commit `data/companies.txt`,
   the touched `data/metadata/*.json` shards, and (if created)
   `data/metadata/15-locations.json`.
7. Delete the scratch `data/locations-batch*.txt` files once merged — they
   aren't read by the build, only `apply_locations.py` consumes them.

## Notes

- Country already exists on most entries; this pass mainly **adds city**
  and **production base**, and fills in country where it was missing.
- Don't duplicate the ~102 already-detailed gigafactory/plant entries
  (`data/metadata/14-gigafactories.json`) — those already have precise
  per-plant city/status/chemistry. This workflow is for giving the
  *corporate* entities (and everyone else) their own HQ + production info.
- `apply_locations.py` never overwrites an existing metadata profile — it
  merges `production_base` into whatever record already exists for that
  entity (in whichever shard it lives), or creates a minimal new one only
  if the entity has no profile yet.
