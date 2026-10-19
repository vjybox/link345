# Working with multiple AI tools (ChatGPT + Claude) without corrupting data

You're bringing ChatGPT in to review/revise/enrich content alongside the
workflows already built in this repo. That's fine and even recommended (the
location/baseline prompt already asks for 2–3 AI tools to cross-check) — but
a few rules keep it from quietly corrupting the dataset. Each rule below maps
to a real bug this project already hit once.

## The one golden rule: ChatGPT produces text, scripts touch files

Never ask ChatGPT (or any AI) to directly rewrite `companies.txt`,
`data/metadata/*.json`, or `data/about.json` as "the final file." Always have
it output in the **same structured formats** this repo already defines —
the pipe-delimited lines from `data/LOCATION_PROMPT.md`, the three labeled
blocks from `data/ENRICHMENT_PROMPT.md` — and merge that output through the
existing tools (`tools/apply_locations.py`, manual paste into the right
metadata shard, `tools/enrich_about.py`'s about.json format). The scripts are
where the safety checks live (fill-gap protection, exact-match keys, build
validation); free-form file edits bypass all of them.

**Give ChatGPT the actual prompt file**, not a paraphrase — paste
`LOCATION_PROMPT.md` / `ENRICHMENT_PROMPT.md` verbatim into the ChatGPT
conversation before asking it to fill in a batch. An AI guessing at the
format from memory will drift (different field names, wrong enum values,
invented JSON structure) and the merge script won't recognize its output.

## Cross-check in parallel, don't chain-revise

Use ChatGPT as one of the **independent** sources in the cross-check step
(run the same prompt + batch through Claude/ChatGPT/Gemini, compare, keep
what agrees), not as a reviser that edits Claude's prior output line-by-line.
Sequential "AI revises AI's text" tends to silently compound small drifts —
a number gets rounded, a hedge gets dropped, a one-liner picks up marketing
language — with no record of what changed or why. Independent generation +
manual reconciliation (or a quick web search when they disagree) is slower
per batch but each pass is actually self-correcting.

## Default to fill-gap, never blanket-overwrite

`tools/apply_locations.py` only fills *empty* fields by default — it already
refuses to let a bulk pass clobber a hand-curated profile. If you specifically
want ChatGPT to **correct** something already in the data (not just fill a
gap), that's a deliberate `--overwrite` run on a small, named batch — review
the diff yourself before committing, same as reviewing a PR. Don't run
`--overwrite` as a routine default "to be safe"; that inverts the safety net.

## Never trust an exact number or URL from a single source

This bit us twice already: gigafactory capacity figures are contested/revised
across sources, and a hallucinated-but-plausible-looking URL is the easiest
thing for any AI to get subtly wrong. Treat GWh/$ figures and URLs as
**verify-or-omit**, regardless of which AI produced them — if ChatGPT and
Claude disagree on a number, or only one of them gave one, don't average them
or guess which to trust: look it up, or leave the field blank. An empty field
costs nothing; a wrong one looks authoritative and spreads (it gets copied
into the auto-generated one-liner, the About paragraph, search snippets...).

## The metadata-key trap applies no matter who writes the key

If ChatGPT proposes a metadata key like `"sunwoda"` for a corporate entity
that also has its own same-named plant entry elsewhere in the dataset, the
build's `resolve()` will silently attach it to whichever entry has the
*shorter* cleaned name — possibly the plant, not the company (this exact bug
hit `sunwoda`/`prologium`/`svolt` in Batch A). Always run `python3 build.py`
after merging anything and read the `[warn]` lines; a key that resolves to
the wrong entry won't warn at all, so for anything ChatGPT proposes as a new
*key* (not just field values), spot-check the resulting page actually shows
the entity you meant.

## Always validate after merging, regardless of source

Same checklist every time, no exceptions for "ChatGPT already checked it":
```bash
python3 build.py        # watch for [warn] unmatched-key lines
```
then spot-check 3–5 of the touched `dist/e/*.html` pages for invented
specifics, and a quick link-integrity pass if you touched many entries at
once (ask Claude Code to run the full regression — link check + Blogger XML
validity — it's cheap and has caught real issues before).

## Git stays single-writer

ChatGPT has no access to this repo — you're always the one applying its
output and running `git commit`/`push`. The only git discipline that matters
is the one already in use: **pull before you start a session, push promptly
after**, so a Claude Code session and your local ChatGPT-assisted edits don't
diverge. If a push ever rejects with "diverged," that's not data loss — it
just means pull-merge (not `--force`) before retrying; every divergence this
project has hit so far merged clean with zero conflicts because the sessions
touched different files or different keys.

## Quick reference

| You want ChatGPT to... | Safe way | Unsafe way |
|---|---|---|
| Fill in HQ/baseline facts | Paste `LOCATION_PROMPT.md` + names, get pipe lines, merge via script | Ask it to "update companies.txt" directly |
| Write/improve a one-liner or About paragraph | Independent generation, cross-check against Claude's, reconcile by hand | Ask it to "revise this paragraph" in place, repeatedly |
| Propose a new relationship edge | Give it `METADATA.md`'s relation list + the two exact keys, verify the claim is public/documented | Let it invent a plausible-sounding key or relation type |
| Double-check a number/URL | Treat disagreement as "go verify," not "pick one" | Average, round, or trust whichever "sounds right" |
