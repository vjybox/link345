# Baseline Metadata — Enrichment Prompt (HQ + core facts)

The **minimum-requirement** metadata every entry should have, in one
pipe-delimited pass you can run across the whole list and cross-check across
multiple AI tools. This is the *shallow-but-universal* companion to
[`ENRICHMENT_PROMPT.md`](ENRICHMENT_PROMPT.md) (which does *deep* type-specific
profiles for the spine): run this over **all** entries to give every page a
real summary, HQ, founding year, ownership and website; run the deep prompt
only where you want chemistry / form-factor / key-IP detail.

## The minimum set (per entry)

| Field | Why it's minimum | Applies to |
| --- | --- | --- |
| **One-liner** | The single highest-value field — becomes the page summary + card subtitle. Without it a page is just a name. | everything |
| **Type** | Corrects the auto-guessed entity type; frames the whole page (Corporate vs Facility vs People…). | everything |
| **HQ City + Country** | Locates the entry; powers the country hubs + map. | everything |
| **Founded** | Universal, low-risk credibility signal. | orgs/companies (blank for people/plants) |
| **Ownership** | Public / Private / State-owned — key filter dimension. | companies |
| **Website** | Drives the logo + official-link. Highest hallucination risk — see rules. | orgs/companies |
| Production base(s) | *Optional bonus* — where it manufactures, if different from HQ. | manufacturers |

---

## The prompt

````text
For each company/organization below, return ONE LINE in EXACTLY this
pipe-delimited format, nothing else (no numbering, no markdown, no commentary):

Name | Type | HQ City | HQ Country | Founded | Ownership | Website | Production base(s) | One-liner

Column rules (leave ANY column BLANK rather than guessing — an empty column is
always better than a wrong value):
- Type: one of Corporate | Facility | People | Research | Institution | Media
- HQ City / HQ Country: current legal headquarters, plain English
  ("South Korea", not "Korea, Republic of").
- Founded: 4-digit year only. Blank for people, plants, and anything you're
  unsure of.
- Ownership: one of Public | Private | Private (VC) | State-owned | Subsidiary
  | Nonprofit | Government. Blank if unknown.
- Website: the REAL official homepage only (https, no path, no tracking). If
  you are not certain of the exact domain, LEAVE IT BLANK — do not construct a
  plausible-looking URL. This is the #1 thing to get wrong.
- Production base(s): main manufacturing site(s) ONLY if they differ from HQ,
  as "City1 (Country1); City2 (Country2)". Blank if same as HQ or unknown.
- One-liner: <= 90 characters, factual, specific, NO marketing words
  (no "leading", "innovative", "world-class"). E.g. "Korean pouch-cell maker;
  Ford BlueOval SK JV" — not "a leading provider of advanced solutions".

Output nothing but the pipe lines, one per company, no header row.

Companies:
<PASTE 20–40 NAMES HERE, ONE PER LINE>
````

## Worked example

Input:
```
Rivian
Sunwoda Electronic
Prof. Jeff Dahn
```

Output:
```
Rivian | Corporate | Irvine | United States | 2009 | Public | https://rivian.com |  | US maker of electric pickups, SUVs and delivery vans
Sunwoda Electronic | Corporate | Shenzhen | China | 1997 | Public | https://www.sunwoda.com | Shenzhen & Zhejiang (China) | Chinese maker of consumer-electronics and EV battery cells
Prof. Jeff Dahn | People | Halifax | Canada |  |  |  |  | Li-ion lifetime researcher; Tesla's academic partner at Dalhousie University
```
(Founded/Ownership/Website blank for the person; Production base blank for
Rivian since it's near HQ.)

## Cross-checking + merge workflow

1. Take 20–40 names from one sector/category.
2. Run the prompt through **2–3 AI tools** (e.g. Claude, ChatGPT, Gemini).
3. Compare line by line. Keep what agrees; where they differ or one is blank,
   spot-check with a quick web search instead of trusting one tool. **Websites
   especially** — verify the domain resolves to the real company.
4. Save the reconciled lines to a text file, e.g. `data/baseline-batch1.txt`
   (a header row is fine — the script reads column names from it).
5. Merge:
   ```bash
   python3 build.py                                  # refresh dist/directory.json
   python3 tools/apply_locations.py data/baseline-batch1.txt
   python3 build.py                                  # apply + check for [warn] lines
   ```
6. Review `data/baseline-batch1.misses.txt` (unmatched names — usually a
   fuller/shorter name form), spot-check a few `dist/e/` pages, then commit
   `data/companies.txt` + the touched `data/metadata/*.json` shards. Delete the
   scratch `baseline-batch*.txt` once merged.

## Safety (how the merge protects your curated data)

`tools/apply_locations.py` is **fill-gap by default**: it only sets a field
that's currently *empty*, so a bulk baseline pass will **never overwrite** the
327 hand-curated profiles (or an existing country/URL). Pass `--overwrite` only
when you deliberately want the new values to win. `production_base` and any
metadata field are merged into an entity's *existing* record (in whatever shard
it lives), never a duplicate key. Header names are matched flexibly, so you can
run a subset of columns (e.g. just `Name | Website`) in a later pass.
