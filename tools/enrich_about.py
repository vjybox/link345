#!/usr/bin/env python3
"""Batch-write the per-entry "About" paragraph using a LOCAL Ollama model.

Free, unlimited, no API key, no cloud. Writes data/about.json (keyed by the
entry's eid); build.py merges it into every content page (dist/e/<slug>.html)
and the Blogger import XML, overriding the auto-composed prose.

Setup (once):
    # install Ollama from https://ollama.com  (Mac/Windows/Linux, free)
    ollama pull llama3.2          # ~2 GB; or: mistral, qwen2.5, phi3 …
    ollama serve                  # usually already running as a service

Run:
    python3 build.py              # refresh dist/directory.json first
    python3 tools/enrich_about.py --model llama3.2          # all entries
    python3 tools/enrich_about.py --seeded-only             # curated first
    python3 tools/enrich_about.py --sector "Cells & Chemistry" --limit 50
    python3 build.py              # rebuild pages with the new paragraphs

It resumes automatically (skips entries already written) and saves after every
entry, so you can stop and restart any time. No third-party packages — stdlib
only (urllib talks to the local Ollama HTTP endpoint).
"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = ROOT / "dist" / "directory.json"
OUT = ROOT / "data" / "about.json"

# Reuse the relation taxonomy from the build (single source of truth).
sys.path.insert(0, str(ROOT))
from build import REL_PROSE  # noqa: E402

SYSTEM = (
    "You write short, neutral, factual company/entity profiles for an industry "
    "directory. Given the facts, write 2 to 4 complete sentences. Rules: use "
    "ONLY the facts provided plus well-established public knowledge; never "
    "invent numbers, dates, tickers, or relationships that are not given; no "
    "marketing words (leading, innovative, world-class, cutting-edge); neutral "
    "encyclopedic tone. Output ONLY the paragraph — no title, no preamble, no "
    "quotation marks, no bullet points."
)

VERBS = REL_PROSE


def stage_of(payload, sector):
    for st in payload.get("stages", []):
        if sector in st["sectors"]:
            return st["n"]
    return "Enablers"


def facts_for(e, payload, rels):
    """A compact, plain-text fact sheet handed to the model."""
    lines = [f"Name: {e['n']}",
             f"Sector: {e['s']} (category: {e.get('cn','')})",
             f"Loop stage: {stage_of(payload, e['s'])}"]
    if e.get("co"):
        lines.append(f"Country: {e['co']}")
    if e.get("one"):
        lines.append(f"Summary: {e['one']}")
    m = e.get("m") or {}
    for k in ("type", "status", "ownership", "founded", "ticker", "product",
              "chemistry", "form_factor", "deployment", "target", "key_ip",
              "extraction", "facility_type", "capacity", "strategic_role",
              "city", "institution_type", "funding_source", "title",
              "expertise", "esg", "media_type"):
        if m.get(k):
            lines.append(f"{k.replace('_',' ').title()}: {m[k]}")
    if e.get("tech"):
        lines.append(f"Tags: {', '.join(e['tech'])}")
    out = [r for r in (rels.get(e["eid"]) or []) if r["d"] == "out"][:6]
    for r in out:
        lines.append(f"Relationship: {VERBS.get(r['r'], r['r'].lower())} {r['n']}")
    return "\n".join(lines)


def clean(text):
    text = (text or "").strip()
    if text[:1] in "\"'“”" and text[-1:] in "\"'“”":
        text = text[1:-1].strip()
    # drop a leading "About X:" / "Profile:" style preamble line
    for lead in ("about ", "profile:", "here is", "here's"):
        if text.lower().startswith(lead):
            text = text.split(":", 1)[-1].strip() if ":" in text[:40] else text
    return " ".join(text.split())


def ask_ollama(host, model, facts, temperature, timeout):
    prompt = f"{SYSTEM}\n\nFacts:\n{facts}\n\nProfile paragraph:"
    body = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": temperature},
    }).encode("utf-8")
    req = urllib.request.Request(host.rstrip("/") + "/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return clean(json.loads(resp.read().decode("utf-8")).get("response", ""))


def main():
    ap = argparse.ArgumentParser(description="Generate 'About' paragraphs via local Ollama.")
    ap.add_argument("--model", default="llama3.2")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--limit", type=int, default=0, help="max entries this run (0 = all)")
    ap.add_argument("--sector", default="", help="only this mega-sector")
    ap.add_argument("--seeded-only", action="store_true", help="only entries with curated metadata")
    ap.add_argument("--overwrite", action="store_true", help="regenerate even if present")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args()

    if not DIRECTORY.exists():
        sys.exit("dist/directory.json not found — run `python3 build.py` first.")
    payload = json.loads(DIRECTORY.read_text("utf-8"))
    rels = payload.get("rels", {})
    entries = payload["entries"]

    done = {}
    if OUT.exists():
        done = {k: v for k, v in json.loads(OUT.read_text("utf-8")).items()
                if not k.startswith("_")}

    # connectivity check with a clear message
    try:
        urllib.request.urlopen(args.host.rstrip("/") + "/api/tags", timeout=5).read()
    except Exception:
        sys.exit(f"Cannot reach Ollama at {args.host}. Start it with `ollama serve` "
                 f"and pull a model, e.g. `ollama pull {args.model}`.")

    queue = []
    for e in entries:
        if args.sector and e["s"] != args.sector:
            continue
        if args.seeded_only and not e.get("m"):
            continue
        if e["eid"] in done and not args.overwrite:
            continue
        queue.append(e)
    if args.limit:
        queue = queue[:args.limit]

    total = len(queue)
    if not total:
        print("Nothing to do (all matching entries already have an 'about').")
        return
    print(f"Generating {total} paragraphs with '{args.model}' … (Ctrl-C to stop; progress is saved)")

    def save():
        OUT.write_text(json.dumps(
            {"_doc": "Per-entry 'About' paragraphs keyed by eid; generated by "
                     "tools/enrich_about.py. Merged into content pages by build.py.",
             **done}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    t0 = time.time()
    for i, e in enumerate(queue, 1):
        facts = facts_for(e, payload, rels)
        try:
            para = ask_ollama(args.host, args.model, facts, args.temperature, args.timeout)
        except KeyboardInterrupt:
            save(); sys.exit("\nStopped — progress saved.")
        except (urllib.error.URLError, TimeoutError) as ex:
            print(f"  [skip] {e['n']}: {ex}")
            continue
        if len(para) < 25:      # guard against empty/garbage output
            print(f"  [skip] {e['n']}: model returned too little")
            continue
        done[e["eid"]] = para
        if i % 10 == 0 or i == total:
            save()
            rate = i / max(1e-6, time.time() - t0)
            print(f"  {i}/{total}  ({rate:.1f}/s)  last: {e['n'][:40]}")
    save()
    print(f"[ok] wrote {OUT} ({len(done)} paragraphs). Run `python3 build.py` to apply.")


if __name__ == "__main__":
    main()
