# Mycelium — Session Handoff

Carry this into the next chat so context isn't lost. Last updated: 2026-05-20.

## What this project is

Self-hosted media pipeline (Flask + SQLite + React SPA) that turns watchlist
clicks into Jellyfin-ready `.strm` files streaming from TorBox. Runs as one
Docker container on a Synology NAS.

- **Live deployment (source of truth):** NAS at
  `/volume1/docker/jelly-stack/webhook` — this directory IS the git repo,
  on branch `main`, remote `github.com/corveck79/mycelium`.
- **Update flow on NAS:** `git pull origin main && docker compose up -d --build`.
  Working tree is clean; data lives in `./data` (DB, `.strm`, settings) and
  survives rebuilds.
- **App URLs:** dashboard `http://10.0.0.10:8088/ui`, SPA `http://10.0.0.10:8088/app/`.
  Jellyfin at `http://10.0.0.10:8096`.

---

## Current state (end of session 2026-05-20)

Everything is on `main`. The NAS needs a `git pull + rebuild` to pick up recent
changes.

### What to do right now on the NAS

```bash
git pull origin main
docker compose up -d --build
```

Then in order:
1. **Admin → Repair broken strm files** — fixes movies with expired direct TorBox CDN URLs
2. **Dashboard → Generate NFOs** — refreshes posters/metadata for any new folders
3. **Dashboard → Run Cleanup** — merges duplicate series/movie folders, renames messy names
4. Jellyfin **Scan All Libraries**

---

## Architecture summary

```
User → SPA (/app/) or Seerr webhook → processor.py
  → Zilean (local) + Torrentio (fallback, with browser User-Agent)
  → debrid.check_cached_multi() → pick best cached release
  → TorBox add_magnet() (or catbox lazy register)
  → strm_generator.py writes .strm + .nfo + poster.jpg + fanart.jpg
  → Jellyfin refresh

On play (catbox mode):
  Jellyfin → /stream/<token> → catbox.materialize()
    → find/re-add torrent in TorBox → requestdl → 302 redirect → TorBox CDN
```

**Two modes for .strm files:**
- **Catbox mode** (`CATBOX_MODE=true` + `CATBOX_LAZY_ADD=true`): `.strm` contains
  `http://10.0.0.10:8088/stream/<token>`. Proxy URL, always fetches a fresh CDN URL
  on play. Recommended — works forever.
- **Direct mode**: `.strm` contains a TorBox `requestdl` CDN URL. Expires after ~24h.
  The Admin → Repair button fixes these by relinking to a catbox token.

---

## All changes shipped (this + previous session — all on `main`)

### Most recent (this session)
| Commit | Change |
|--------|--------|
| `abea902` | **Repair broken .strm files**: `repair_expired_strms()` in `strm_generator.py` + `POST /ui/api/repair-strms` + Admin → Maintenance panel button. Detects expired direct CDN URLs in .strm files, relinks to catbox token or deletes + requeues. |
| `7f79956` | **Failed requests UI**: `GET /ui/api/requests/failed` + `POST /ui/api/requests/<id>/retry`. Requests page now shows a "Failed requests" section with per-row ↺ Retry button. |
| `46de8f0` | **Torrentio 403 fix**: Added browser `User-Agent` + `Accept` headers to all Torrentio requests (`_HTTP_HEADERS` in `torrentio.py`). Cloudflare was blocking plain Python requests from NAS/datacenter IPs. |
| `b10e8ef` | **Radarr/Sonarr import progress**: Admin page shows live progress bar, done/total/%, added/skipped/errors during bulk import. Auto-polls at 1 s while running, 5 s idle. |
| `f22104e` | **Radarr/Sonarr settings fix**: Import + test endpoints now read from settings DB (`settings.get("RADARR_URL", ...)`) instead of startup-time env constants. Fixes "url + api_key required" error. |
| `831e9b3` | **Auth fix**: `is_admin()` now returns `True` when auth is disabled (single-user mode). Fixes "admin required" on Radarr/Sonarr test when `AUTH_ENABLED=false`. |
| `4e3b3e9` | **Movie folder cleanup**: `rename_messy_movie_folders()` + `merge_movie_duplicates()` in `cleanup.py`. Reads title/year/imdb_id from .nfo, renames folder + .strm + .nfo to `Title (Year)` format. Merges duplicate folders with same IMDb ID. |
| `02c9496` | **Library episode drilldown**: Series panel in Library tab shows expandable rows per series with season numbers and episode badges. Uses new `GET /ui/api/library/series-episodes` endpoint. |
| `c858165` | TMDB fallback in series folder rename: if series not in `monitored_series` DB, looks up canonical title via `tmdb.find_by_imdb` + `get_show_info`. |
| `c4702d5` | **Series folder rename**: `rename_messy_series_folders()` reads IMDb from `tvshow.nfo`, looks up canonical title in DB/TMDB, renames folder. Fixes `www UIndex org - Show` → `Show (year)`. |

### Previous session
| Commit | Change |
|--------|--------|
| `238b3d2` | Complete catbox + clean architecture refactor: `processor.py` lazy series registration, `upgrader.py` catbox-aware auto-upgrade. |
| `a66fa2a` | Local image fetcher: `nfo_generator.fetch_local_images()` downloads poster.jpg + fanart.jpg (TMDB) and episode stills. Hooked into startup, `/ui/generate-nfos`, and library import. |
| `2795439` | `merge_series_duplicates()` in `cleanup.py`: groups series folders by IMDb ID from tvshow.nfo, merges .strm files, removes duplicates. |
| `335cf40` | `EXCLUDE_LANGUAGES` setting: detects Russian (keywords + Cyrillic) and blocks them. |

---

## Key files

| File | Purpose |
|------|---------|
| `processor.py` | Request → search → cache-check → add to TorBox (or catbox lazy register) |
| `strm_generator.py` | Write `.strm`/`.nfo`/images; `repair_expired_strms()` for broken links |
| `catbox.py` | Lazy TorBox materialization for `/stream/<token>` |
| `cleanup.py` | Dedup `.strm`, merge series/movie folders, rename messy folder names |
| `upgrader.py` | Auto-upgrade quality + season-pack consolidation (catbox-aware) |
| `torrentio.py` | Torrent candidate fetch + ranking + language filtering |
| `arr_import.py` | Radarr/Sonarr bulk import (reads settings from DB, not env) |
| `auth.py` | Session login, proxy-auth trust, multi-user roles |
| `db.py` | SQLite access: requests, virtual_items, monitored_series, retry_queue, … |
| `tmdb.py` | TMDB API: search, images, episode stills, IMDb↔TMDB ID mapping |
| `settings.py` | Runtime-editable settings (reads DB first, `.env` fallback) |
| `nfo_generator.py` | Write `.nfo` sidecars + fetch local images |
| `app.py` | Flask app, scheduler, all UI/API endpoints |
| `retry_queue.py` | Exponential backoff retry scheduler (60m / 6h / 24h) |

---

## Known remaining issues / next steps

- **Series duplicates** in Jellyfin: still need cleanup run on NAS with latest code.
  Most should merge automatically via `rename_messy_series_folders` + `merge_series_duplicates`.
- **Missing episodes**: user asked "hoe vullen we gemiste afleveringen aan?" — not yet
  implemented. Options: scan Library episode view → detect gaps → re-run monitor for
  those seasons; or a "fill missing" button per series in the Library tab.
- **Radarr/Sonarr import verification**: needs a test run after the settings fix.
- **Torrentio 403 fix**: deployed in code, not yet tested on NAS (needs rebuild).

---

## Workflow notes / gotchas

- Work directly on `main` (user's preference).
- `data/` is gitignored — can't inspect DB or media from a cloud session.
  Ask user to run `find`/`ls`/`sqlite3` on the NAS when needed.
- POST endpoints are CSRF-protected by default → trigger via dashboard buttons, not curl.
  CSRF-exempt endpoints: `/api/run-cleanup`, `/api/generate-nfos`, `/ui/api/repair-strms`,
  `/ui/api/requests/<id>/retry`, `/ui/api/requests/failed` (GET, no CSRF needed).
- Single gunicorn worker, 8 threads → in-process state (catbox URL cache, scan-burst
  detector, retry queue) is shared and safe.
- Scheduler intervals need a container restart to change; most settings are hot-reloadable
  via Settings tab without restart.
- `settings.get("KEY", default)` reads settings DB first, then falls back to env/config.py.
  Always use `settings.get()` in endpoints — never `config.KEY` directly — or settings
  changes in the UI won't take effect.
- Jellyfin compose: `/volume1/docker/jellyfin/docker-compose.yml` (separate from the app
  compose at `/volume1/docker/jelly-stack/webhook/`).
- CATBOX_HOST must be the externally reachable URL that Jellyfin can reach
  (currently `http://10.0.0.10:8088`). This goes into the .strm file itself.
