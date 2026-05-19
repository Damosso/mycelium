"""Generate Kodi/Jellyfin-compatible NFO sidecar files alongside .strm files.

Movies: movies/Title (Year)/Title (Year).nfo
Series: series/Title/tvshow.nfo

Jellyfin reads these to get the exact IMDb ID, so it can fetch metadata and
posters without guessing from the folder name.
"""
import logging
import re
from pathlib import Path

import db
from config import MEDIA_PATH

log = logging.getLogger(__name__)

_YEAR_RE = re.compile(r"\((\d{4})\)$")


def _movie_nfo(title: str, year: int | None, imdb_id: str) -> str:
    year_tag = f"\n  <year>{year}</year>" if year else ""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        "<movie>\n"
        f"  <title>{title}</title>{year_tag}\n"
        f'  <uniqueid type="imdb" default="true">{imdb_id}</uniqueid>\n'
        "</movie>\n"
    )


def _tvshow_nfo(title: str, imdb_id: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        "<tvshow>\n"
        f"  <title>{title}</title>\n"
        f'  <uniqueid type="imdb" default="true">{imdb_id}</uniqueid>\n'
        "</tvshow>\n"
    )


def _write(path: Path, content: str) -> bool:
    if path.exists():
        return False
    try:
        path.write_text(content, encoding="utf-8")
        log.info("Wrote NFO: %s", path)
        return True
    except Exception as exc:
        log.warning("Could not write NFO %s: %s", path, exc)
        return False


def generate_all() -> dict:
    """Write missing NFO files for all movies and series using IMDb IDs from DB."""
    media = Path(MEDIA_PATH)
    items_by_title = {m["title"]: m["imdb_id"] for m in db.get_media_items()}

    movies = series = 0

    movies_dir = media / "movies"
    if movies_dir.is_dir():
        for folder in movies_dir.iterdir():
            if not folder.is_dir():
                continue
            imdb_id = items_by_title.get(folder.name)
            if not imdb_id or imdb_id.startswith("unknown_"):
                continue
            m = _YEAR_RE.search(folder.name)
            year = int(m.group(1)) if m else None
            title = _YEAR_RE.sub("", folder.name).strip() if m else folder.name
            if _write(folder / f"{folder.name}.nfo", _movie_nfo(title, year, imdb_id)):
                movies += 1

    series_dir = media / "series"
    if series_dir.is_dir():
        for folder in series_dir.iterdir():
            if not folder.is_dir():
                continue
            imdb_id = items_by_title.get(folder.name)
            if not imdb_id or imdb_id.startswith("unknown_"):
                continue
            if _write(folder / "tvshow.nfo", _tvshow_nfo(folder.name, imdb_id)):
                series += 1

    log.info("NFO generation complete: %d movie(s), %d series", movies, series)
    return {"movies": movies, "series": series}
