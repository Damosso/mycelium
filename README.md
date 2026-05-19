# 🍄 Mycelium

> *`myc3l1um` — the hidden network beneath your media library.*

Mycelium is a self-hosted automation service that connects [Jellyseerr/Overseerr](https://jellyseerr.dev/), [TorBox](https://torbox.app/), and [Jellyfin](https://jellyfin.org/) into a single intelligent stack. It receives requests, hunts down the best release across [Zilean](https://github.com/iPromKnight/zilean) and [Torrentio](https://torrentio.strem.fun/), adds it to TorBox, and writes `.strm` files Jellyfin can play — all in ~30 seconds, with zero local storage.

Built specifically for the **Jellyfin + TorBox + Synology NAS** stack — no FUSE, no rclone, no Plex required.

---

## ✨ Features

### Core flow
- 🪝 **Seerr webhook integration** — auto-process every approved request
- 🔎 **Zilean + Torrentio search** with smart fallback ordering
- ⚡ **TorBox cache-first** strategy (instant adds for cached releases)
- 📝 **Smart `.strm` generation** with Jellyfin-friendly naming (`Title (Year)/Title (Year).strm`, `Series/Season XX/Series S01E01.strm`)
- 🎬 **Library refresh** triggered automatically

### Catbox mode (lazy materialization)
Inspired by [elfhosted's CatBox](https://docs.elfhosted.com/app/catbox/) — items are virtual in your library until you press play. Stays within TorBox's 30-day cache retention while supporting effectively unlimited library size.
- `.strm` files contain a proxy URL pointing at this service
- On playback: re-add to TorBox if released, fetch fresh CDN URL, 307 redirect
- Idle items released after `CATBOX_IDLE_MINUTES`

### Smart picks
- **Per-show quality overrides** — per-IMDB quality/4K/HEVC preferences
- **Audio language preference** — boost releases matching your language(s)
- **Auto-upgrade** — background scan replaces 720p with cached 1080p/4K when available
- **Season-pack consolidation** — swap N per-episode torrents for 1 cached pack
- **Trending pre-cache** — auto-add TMDB trending if already cached

### Robustness
- ⚡ **SQLite WAL** mode + integrity check on startup
- 🔒 **Per-IMDB mutex** prevents double-processing
- 🚫 **Failed-hash blacklist** after configurable retry threshold
- ↻ **Smart retry backoff** (60m / 6h / 24h)
- 🩺 **Self-healing** strm probe + cleanup task
- 🐶 **Watchdog** — deadman switch + disk space warnings
- 💾 **Daily DB backup** (14 retained)
- 🚑 **Recovery wizard** — one-button repair (integrity → cleanup → library import → strm scan)
- 📦 **Library import** — rebuild DB from `.strm` files after disaster

### UX
- 🖥 **Polished web dashboard** at `/ui` — 11 tabs, sortable tables, TMDB posters, dark/light theme
- 🔍 **Manual search & pick** — see every Zilean/Torrentio candidate, pick exactly which to add
- 🔧 **Runtime settings** — toggle Catbox mode, quality filters, etc. without restart
- 📊 **Live stats** — quality distribution, source win rate, latency, retry queue
- 🩻 **Service health** dots in topbar (Zilean / Torrentio / TorBox / TMDB / Jellyfin / Seerr)
- 🛎 **Discord + Telegram** notifications on success/failure
- 🎹 **Keyboard shortcuts** (1-9, 0 for tabs)

### Integrations
- **Seerr webhook** at `POST /webhook`
- **TorBox push notifications** at `POST /torbox-webhook`
- **OpenSubtitles** auto-download for new movies (optional)
- **Continue-watching priority** via Jellyfin Resume API
- **RealDebrid** scaffolding for multi-debrid setups (informational)

---

## 🚀 Quick start

### Prerequisites
- Docker + Docker Compose
- A TorBox account ([torbox.app](https://torbox.app))
- Jellyseerr or Overseerr running
- Jellyfin running
- (Optional) Zilean instance for local-first search

### Install

```bash
git clone https://github.com/corveck79/mycelium.git
cd mycelium
cp .env.example .env
# Edit .env — at minimum set TORBOX_API_KEY
nano .env
docker compose up -d --build
```

Then in Seerr: **Settings → Notifications → Webhook**, point at `http://<your-nas>:8088/webhook`.

Dashboard at `http://<your-nas>:8088/ui`.

### First-run

1. Open the dashboard, go to **Settings**
2. Toggle `CATBOX_MODE` if you want lazy materialization
3. Set your `AUDIO_LANGUAGE_PREFERENCE` (e.g. `nl,en`)
4. Configure notifications under the same tab
5. Click **🚑 Recovery wizard** on Overview to baseline the library

---

## ⚙️ Configuration

All settings live in `.env` (see `.env.example` for the full reference). Most are **hot-reloadable** from the Settings UI tab — only scheduler intervals require a restart.

Key knobs:

| Variable | What it does |
|---|---|
| `TORBOX_API_KEY` | **Required.** Your TorBox API key |
| `CATBOX_MODE` | Enable lazy materialization (default off) |
| `CATBOX_HOST` | Externally reachable URL for proxy `.strm` URLs |
| `QUALITY_PREFERENCE` | Comma-separated preference order |
| `AUDIO_LANGUAGE_PREFERENCE` | Languages to prefer (e.g. `nl,en`) |
| `AUTO_UPGRADE_ENABLED` | Periodic upgrade scan |
| `SEASON_PACK_CONSOLIDATION_ENABLED` | Swap per-episode for packs |
| `DISCORD_WEBHOOK_URL` / `TELEGRAM_BOT_TOKEN` | Optional notifications |

---

## 🏗 Architecture

```
                ┌──────────────┐
                │   Seerr      │
                └──────┬───────┘
                       │ webhook
                       ▼
            ┌──────────────────────┐
   Zilean ◄─┤      MYCELIUM        ├─► TMDB
 Torrentio◄─┤  (this service)      │
            │  ┌────────────────┐  │
            │  │  Catbox proxy  │  │
            │  └────────────────┘  │
            └──────┬────────┬──────┘
                   │        │
              add  ▼        ▼  refresh
            ┌──────────┐ ┌──────────┐
            │  TorBox  │ │ Jellyfin │
            └────┬─────┘ └──────────┘
                 │  CDN
                 ▼
              client
```

---

## 📜 License

MIT — do whatever, just don't blame me if your library disappears.

## 🙏 Credits

- [elfhosted](https://elfhosted.com) for the CatBox concept that inspired the lazy-materialization mode
- [TorBox](https://torbox.app) for being a reasonably-priced debrid that doesn't suck
- [Jellyseerr](https://jellyseerr.dev) and [Jellyfin](https://jellyfin.org) for the rest of the ecosystem
