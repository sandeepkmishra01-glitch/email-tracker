# Email Tracker

Email open and click tracking built with FastAPI (Gmail and Outlook on the web via the Chrome/Edge extension). Each recipient gets a unique token. A 1x1 pixel records opens, and rewritten links record clicks.

## Run locally
```
python -m venv .venv && .venv/Scripts/activate   # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # set ADMIN_PASS
uvicorn app.main:app --reload
```
Open http://localhost:8000 (HTTP Basic auth: `ADMIN_USER` / `ADMIN_PASS`; the dashboard returns 503 until `ADMIN_PASS` is set). Run tests with `pytest`.

## Deploy on Railway
1. Push this repo to GitHub.
2. Railway → New Project → Deploy from GitHub repo.
3. Add a **PostgreSQL** database to the project. Railway sets `DATABASE_URL`, and the app reads it. Without Postgres, data is lost on redeploy.
4. In the app service, set variables: `ADMIN_USER`, `ADMIN_PASS`, and `BASE_URL` (the public URL, e.g. `https://your-app.up.railway.app`). Optionally set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` and `SMTP_FROM` to send from the app.
5. Settings → Networking → Generate Domain. Healthcheck is `/health` (see `railway.json`).

`BASE_URL` must be the public URL, because it is embedded in every tracked email.

## Endpoints
- Public: `GET /t/{token}.png` (open), `GET /c/{token}/{link_id}` (click), `GET /health`
- Admin (Basic auth): `/`, `/compose`, `/emails/{id}`, `/api/emails`

## Caveats
- Open tracking is approximate. Image blocking and Apple Mail Privacy Protection distort it, and likely proxy or prefetch opens are flagged separately. Clicks are more reliable.
- Disclose tracking to recipients where the law requires it (GDPR/ePrivacy).

## Privacy and security
- The repo holds no secrets. Keep `.env`, `ADMIN_PASS` and `TRACKER_API_KEY` out of git and out of screenshots.
- `ADMIN_PASS` has no default. Without it the dashboard is locked (503), so a missed variable can't expose it.
- IPs are stored truncated (/24 IPv4, /48 IPv6) unless `STORE_FULL_IP=true`. Apple-proxy detection still uses the full IP before truncation.
- On startup, events older than `SCRUB_AFTER_DAYS` (default 90) have their IP and user agent blanked. Open/click timestamps and counts are kept. Set `0` to disable.
- API docs (`/docs`, `/openapi.json`) are disabled; `/robots.txt` disallows crawlers; responses set `nosniff`, `no-referrer` and `X-Frame-Options: DENY`.
- Rotate `TRACKER_API_KEY` in Railway if it leaks, then update the extension's Options.
