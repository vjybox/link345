# Self-hosting on Synology (Docker) — the full stack

This replaces the GitHub Pages / Google Forms / GoatCounter plan in
`NEXT-STEPS.md` with everything running on your own Synology NAS: the
generated site, your own Submit-a-company form, and your own analytics —
all backed by one SQLite file you control.

**What ships:**
- `web` — nginx serving `dist/` (the generated static site) and reverse-
  proxying `/api/*` and `/admin` to the `api` container, so the whole thing
  is reachable on one port.
- `api` — a small Flask service (`server/app.py`) handling form submissions
  and a privacy-friendly analytics beacon, storing both in SQLite.

## 1. Get the repo onto the NAS

Either `git clone` directly on the NAS over SSH (Synology's DSM ships git
in Container Manager's terminal, or install Git Server from Package
Center), or build `dist/` on your own machine and copy the whole repo
folder over via File Station / `rsync`. Either way you need the **whole
repo** on the NAS (not just `dist/`) — `docker-compose.yml`, `docker/`,
and `server/` all need to be there for the build.

## 2. Configure secrets

```bash
cp .env.example .env
```
Edit `.env` and set a real `ADMIN_PASSWORD` (long and random — this guards
`/admin`, which shows all submissions and lets you download them as CSV).
`.env` is gitignored; never commit it.

## 3. Generate the site

```bash
python3 build.py
```
This needs Python 3.11+ on the NAS (or wherever you run it before
copying `dist/` + the rest of the repo over). Re-run this any time
`data/*` or `build.py` changes — `dist/` is bind-mounted into the `web`
container read-only, so there's **no container restart needed** for
content updates; nginx just serves the new files immediately.

## 4. Bring the stack up

In **Container Manager** → Project → Create, point it at the repo folder
(it reads `docker-compose.yml` directly), or over SSH:

```bash
docker compose up -d --build
```

Check both containers are healthy:
```bash
docker compose ps
curl http://localhost:8080/api/health   # {"ok": true}
```

The site is now at `http://<nas-ip>:8080/`. `HOST_PORT` in `.env` controls
that port if 8080 collides with something else on your NAS.

## 5. Expose it (pick one)

- **LAN only**: nothing more to do — browse `http://<nas-ip>:8080/` from
  your network.
- **Public, via Synology's reverse proxy**: DSM Control Panel → Login
  Portal → Advanced → Reverse Proxy → add a rule forwarding your domain
  (with HTTPS/Let's Encrypt, which DSM can issue free) to
  `localhost:8080`. This is the recommended path — one place to manage
  TLS, and the container itself stays on plain HTTP behind it.
- **Public, no port-forwarding**: a Cloudflare Tunnel (free) pointed at
  `localhost:8080` avoids opening any port on your router at all.

Once you have a final public URL, set it as `SITE_BASE` in `build.py`
(search for `SITE_BASE = ""`) and re-run `python3 build.py` — this
unlocks the real sitemap, BreadcrumbList JSON-LD, and absolute Blogger
cross-links.

## 6. Using the admin dashboard

`http://<your-url>/admin` (HTTP Basic Auth, the `ADMIN_USER`/`ADMIN_PASSWORD`
from `.env`) shows:
- pageview counts (today / 7d / 30d / all-time) and top pages — your
  self-hosted analytics, no third party involved.
- every company submission, newest first, with a **Download CSV** button.

Feed that CSV into `tools/import_submissions.py` (see `METADATA.md`) to
turn reviewed submissions into ready-to-merge `companies.txt`/metadata
entries — same review-before-merge discipline as the AI-enrichment
batches.

## Day-to-day operations

| Task | Command |
| --- | --- |
| Update content (data changes) | `python3 build.py` — live immediately, no restart |
| Update the API (`server/app.py` changes) | `docker compose up -d --build api` |
| View logs | `docker compose logs -f api` / `web` |
| Back up the database | `docker compose exec api sqlite3 /data/app.db ".backup /data/backup.db"`, then copy that file off the NAS (or just copy the named volume's file directly — see Synology's Docker volume path under Container Manager → Volume) |
| Restart everything | `docker compose restart` |
| Stop everything | `docker compose down` (data survives — it's in the named volume, not removed by `down`) |

## Security notes

- `/api/submit` has a basic per-IP rate limit (5/hour) to deter spam — it's
  friction, not a CAPTCHA; if spam becomes a real problem, add one.
- **Never expose `/admin` over plain HTTP beyond your LAN.** HTTP Basic Auth
  sends the username/password on every request as trivially-reversible
  Base64, not encryption — over plain HTTP that's readable by anything
  between the visitor and your NAS. Nothing in the stack blocks this by
  itself; it's only safe because step 5's recommended paths (DSM's reverse
  proxy with Let's Encrypt, or a Cloudflare Tunnel) put real TLS in front
  of it. If you ever reach `/admin` and the address bar says `http://`
  from outside your LAN, stop and fix the reverse proxy first. There's
  also no lockout on failed login attempts, so keep `ADMIN_PASSWORD` long.
- The API container never talks to the internet — the only network calls
  are inbound (from nginx) and to the local SQLite file. No data leaves
  your NAS unless you choose to export it.
- The CSV export (`/admin/submissions.csv`) neutralizes formula-injection
  payloads (a submission starting with `=`, `+`, `-`, or `@`, which Excel/
  Sheets would otherwise interpret as a formula when you open the file) —
  no action needed on your part, just worth knowing it's handled.
