# Mycelium — Session Handoff

Carry this into the next chat so context isn't lost. Last updated: 2026-05-20.

## What this project is
Self-hosted media pipeline (Flask + SQLite + React SPA) that turns watchlist
clicks into Jellyfin-ready `.strm` files streaming from TorBox. Runs as one
Docker container.

- **Live deployment (source of truth):** NAS at
  `/volume1/docker/jelly-stack/webhook` — this directory IS the git repo,
  on branch `main`, remote `github.com/corveck79/mycelium`.
- **Update flow on the NAS:** `git pull origin main && docker compose up -d --build`.
  Working tree is clean; data lives in `./data` (DB, `.strm`, settings) and
  survives rebuilds.
- **App URLs:** dashboard `http://10.0.0.10:8088/ui`, SPA `/app/`.
  Jellyfin at `http://10.0.0.10:8096`.

## The problem we were chasing
Jellyfin shows ~200 movies but disk only has **79 movie folders / 79 .strm
files** (verified with `find data/media/movies`). So the duplicates are NOT on
disk — they are **ghost/duplicate entries inside Jellyfin's own database**.

## ROOT CAUSE FOUND (still open)
The app's Jellyfin API key is invalid → every Jellyfin call returns **401**:
```
ERROR [jellyfin] Jellyfin refresh failed: 401
```
Because of this the app cannot (a) trigger a library scan to prune ghosts, nor
(b) run MergeVersions to collapse duplicates. Nothing we do reaches Jellyfin
until this is fixed.

### Next action (do this first)
1. Jellyfin → Dashboard → API Keys → create/verify a key.
2. App → Settings tab → paste Jellyfin API key → **Test** (must go green) → Save.
   Confirm URL is `http://10.0.0.10:8096`.
3. Verify: `docker compose logs --tail=20 mycelium | grep -i jellyfin`
   should show `library refresh accepted`, not `401`.
4. Then run a full Jellyfin scan + let MergeVersions run. Ghost entries share
   the same IMDb ID as the real 79 films, so merge-by-IMDb collapses the count
   toward ~79.

## Changes shipped this session (all on `main`)
- `8b8f5ec` — MergeVersions groups Jellyfin movies by **IMDb/TMDB provider ID**
  (was: by name), so 4K+HD and name-variants collapse into one entry.
  Also: deleting a duplicate/unfixable `.strm` now removes its sibling `.nfo`.
  Files: `jellyfin.py`, `cleanup.py`.
- `9fe182d` — `cleanup.remove_orphan_folders()`: deletes movie/series folders
  with no `.strm` left (leftover `.nfo`/posters), runs first in every cleanup
  pass, then triggers a Jellyfin refresh. File: `cleanup.py`.
- `f1f2aef` — scan-burst probe-guard in `catbox.materialize()`: when many
  distinct tokens are requested in a short window (a library scan), skip the
  TorBox re-add (was costing up to 45s per item × ~200). Real single-title
  playback still re-adds on demand. Covers `/stream` and WebDAV.
  File: `catbox.py`.
- `e250dfb` — README: fixed stale clone URL (`myce` → `mycelium`).

Verified: frontend builds clean (Vite → `static/app/`), all `.py` modules
compile. Cleanup confirmed working in prod logs (`found 442 .strm files`,
`removed 11 duplicate .strm file(s)`).

## Known secondary issues (not yet fixed)
- **Messy series folder names** create duplicate series folders, e.g.
  `www UIndex org    -    FROM` vs `From`, and Cyrillic prefixes like
  `Громовержцы  Thunderbolts`. The torrent-site/Cyrillic prefix stripping
  (`strm_generator._clean_torrent_name`, `cleanup._series_clean_title`) misses
  some of these for SERIES, so they land as separate folders. Movies are fine
  (write-time fuzzy dedup works — see "Skipping duplicate strm" log lines).
- DB vs disk drift: dashboard showed `STRM ∉ DB` and `DB ∉ STRM` counts; not
  addressed.
- **SECURITY:** the user pasted a GitHub PAT (`ghp_...`) into chat earlier and
  was told to revoke it. Confirm it was revoked.

## Workflow notes / gotchas
- Work directly on `main` (user's preference). Develop, commit, push to `main`.
- `data/` is gitignored (DB/media not tracked) — can't inspect media from a
  cloud session; must ask the user to run `find`/`ls` on the NAS.
- `/ui/run-cleanup` and other POST endpoints are CSRF-protected → can't `curl`
  them; trigger via the dashboard buttons (Recovery wiz runs integrity +
  cleanup + import + strm scan).
- Single gunicorn worker, 8 threads → in-process state (e.g. catbox scan-burst
  detector, mylist cache) is shared and safe.
- Scheduler intervals (cleanup, MergeVersions, strm-gen) need a restart to
  change; most other settings are hot-reloadable via Settings tab.
