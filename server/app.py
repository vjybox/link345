"""Self-hosted submission intake + analytics for The Lithium Index.

Replaces Google Forms (Submit a company) and third-party analytics
(GoatCounter/Cloudflare) with a tiny SQLite-backed Flask API, meant to run
on your own Docker host (e.g. Synology Container Manager) behind the nginx
container in this repo's docker-compose.yml.

Endpoints:
  POST /api/submit      -- new company submission (replaces the Google Form)
  POST /api/pageview     -- analytics beacon (replaces GoatCounter/Cloudflare)
  GET  /api/health       -- container healthcheck
  GET  /admin             -- basic-auth dashboard: pageview stats + submissions
  GET  /admin/submissions.csv -- CSV export (feeds tools/import_submissions.py)

No cookies, no IP storage, no third-party calls. Data lives in one SQLite
file (DB_PATH, default /data/app.db -- mount this as a volume so it
survives container restarts; back it up like you would any database).
"""
import csv
import io
import os
import re
import sqlite3
import time
from collections import defaultdict
from functools import wraps

from flask import Flask, g, jsonify, request, Response

DB_PATH = os.environ.get("DB_PATH", "/data/app.db")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
# Comma-separated list of origins this API will accept submissions/pageviews
# from. Leave unset to allow same-origin only (the normal case behind nginx).
ALLOWED_PATH_PREFIX = "/"

app = Flask(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    company_name TEXT NOT NULL,
    official_url TEXT,
    country TEXT,
    category TEXT,
    description TEXT,
    related_companies TEXT,
    submitter_email TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS pageviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    day TEXT NOT NULL,
    path TEXT NOT NULL,
    referrer TEXT
);
CREATE INDEX IF NOT EXISTS idx_pageviews_day ON pageviews(day);
CREATE INDEX IF NOT EXISTS idx_pageviews_path ON pageviews(path);
"""


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.executescript(SCHEMA)
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# --- naive in-memory rate limit: N submissions / IP / hour. Resets on
# container restart, which is fine -- this is spam-friction, not security. ---
_submit_hits = defaultdict(list)
SUBMIT_LIMIT, SUBMIT_WINDOW = 5, 3600


def rate_limited(ip):
    now = time.time()
    hits = [t for t in _submit_hits[ip] if now - t < SUBMIT_WINDOW]
    _submit_hits[ip] = hits
    if len(hits) >= SUBMIT_LIMIT:
        return True
    hits.append(now)
    return False


def requires_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not ADMIN_PASSWORD:
            return Response(
                "Admin dashboard disabled: set ADMIN_PASSWORD in the environment "
                "(see .env.example) and restart the container.", status=503)
        auth = request.authorization
        if not auth or auth.username != ADMIN_USER or auth.password != ADMIN_PASSWORD:
            return Response(
                "Authentication required.", status=401,
                headers={"WWW-Authenticate": 'Basic realm="Lithium Index Admin"'})
        return fn(*args, **kwargs)
    return wrapper


URL_RE = re.compile(r"^https?://[^\s]+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.post("/api/submit")
def submit():
    data = request.get_json(silent=True) or request.form
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if rate_limited(ip):
        return jsonify(ok=False, error="Too many submissions from this network. Try again later."), 429

    company_name = (data.get("company_name") or "").strip()[:200]
    if not company_name:
        return jsonify(ok=False, error="company_name is required"), 400

    official_url = (data.get("official_url") or "").strip()[:500]
    if official_url and not URL_RE.match(official_url):
        return jsonify(ok=False, error="official_url must be a valid http(s) URL"), 400

    submitter_email = (data.get("submitter_email") or "").strip()[:200]
    if submitter_email and not EMAIL_RE.match(submitter_email):
        return jsonify(ok=False, error="submitter_email doesn't look like an email"), 400

    row = (
        company_name,
        official_url,
        (data.get("country") or "").strip()[:100],
        (data.get("category") or "").strip()[:200],
        (data.get("description") or "").strip()[:2000],
        (data.get("related_companies") or "").strip()[:1000],
        submitter_email,
    )
    db = get_db()
    cur = db.execute(
        "INSERT INTO submissions (company_name, official_url, country, category, "
        "description, related_companies, submitter_email) VALUES (?,?,?,?,?,?,?)", row)
    db.commit()
    return jsonify(ok=True, id=cur.lastrowid), 201


@app.post("/api/pageview")
def pageview():
    data = request.get_json(silent=True) or {}
    path = str(data.get("path") or request.referrer or "/")[:300]
    if not path.startswith(ALLOWED_PATH_PREFIX):
        path = "/"
    referrer = str(data.get("referrer") or "")[:300]
    db = get_db()
    db.execute(
        "INSERT INTO pageviews (day, path, referrer) VALUES (date('now'), ?, ?)",
        (path, referrer))
    db.commit()
    return "", 204


@app.get("/api/health")
def health():
    return jsonify(ok=True)


@app.get("/admin")
@requires_admin
def admin_dashboard():
    db = get_db()
    totals = db.execute(
        "SELECT "
        " (SELECT COUNT(*) FROM pageviews WHERE day = date('now')) AS today,"
        " (SELECT COUNT(*) FROM pageviews WHERE day >= date('now','-7 days')) AS d7,"
        " (SELECT COUNT(*) FROM pageviews WHERE day >= date('now','-30 days')) AS d30,"
        " (SELECT COUNT(*) FROM pageviews) AS all_time"
    ).fetchone()
    top_paths = db.execute(
        "SELECT path, COUNT(*) n FROM pageviews WHERE day >= date('now','-30 days') "
        "GROUP BY path ORDER BY n DESC LIMIT 20").fetchall()
    subs = db.execute(
        "SELECT * FROM submissions ORDER BY id DESC LIMIT 200").fetchall()

    def esc(s):
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    rows_html = "".join(
        f"<tr><td>{r['id']}</td><td>{esc(r['created_at'])}</td>"
        f"<td>{esc(r['company_name'])}</td><td>{esc(r['official_url'])}</td>"
        f"<td>{esc(r['country'])}</td><td>{esc(r['category'])}</td>"
        f"<td>{esc(r['status'])}</td></tr>" for r in subs)
    paths_html = "".join(f"<tr><td>{esc(p['path'])}</td><td>{p['n']}</td></tr>" for p in top_paths)

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Lithium Index -- Admin</title>
<style>
body{{font:14px/1.5 -apple-system,system-ui,sans-serif;margin:2rem;color:#111}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}
th,td{{border:1px solid #ddd;padding:6px 10px;text-align:left;font-size:13px}}
th{{background:#f4f4f4}}
.stats span{{display:inline-block;margin-right:2rem;font-size:1.3em;font-weight:600}}
.stats small{{display:block;font-size:.6em;font-weight:400;color:#666}}
a.btn{{display:inline-block;margin:.5rem 0;padding:6px 12px;background:#111;color:#fff;
      text-decoration:none;border-radius:4px;font-size:13px}}
</style></head><body>
<h1>Lithium Index -- Admin</h1>
<div class="stats">
<span>{totals['today']}<small>today</small></span>
<span>{totals['d7']}<small>7 days</small></span>
<span>{totals['d30']}<small>30 days</small></span>
<span>{totals['all_time']}<small>all time</small></span>
</div>
<h2>Top pages (30d)</h2>
<table><tr><th>Path</th><th>Views</th></tr>{paths_html}</table>
<h2>Submissions ({len(subs)} shown, newest first)</h2>
<a class="btn" href="/admin/submissions.csv">Download CSV</a>
<table><tr><th>ID</th><th>Submitted</th><th>Company</th><th>URL</th>
<th>Country</th><th>Category</th><th>Status</th></tr>{rows_html}</table>
</body></html>"""


@app.get("/admin/submissions.csv")
@requires_admin
def admin_submissions_csv():
    db = get_db()
    rows = db.execute("SELECT * FROM submissions ORDER BY id").fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = ["id", "created_at", "company_name", "official_url", "country",
            "category", "description", "related_companies", "submitter_email", "status"]
    w.writerow(cols)
    for r in rows:
        w.writerow([r[c] for c in cols])
    return Response(buf.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=submissions.csv"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
