"""Read-only client for noise_laws.db."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path


log = logging.getLogger("legal_mind")

# Путь по умолчанию: region/data/noise_laws.db
_this_dir = Path(__file__).parent
DEFAULT_PATH = _this_dir / "data" / "noise_laws.db"
DB_PATH = str(DEFAULT_PATH)

# Кэш статей (noise_articles.json)
_ARTICLES_PATH = _this_dir / "data" / "noise_articles.json"
_articles_cache: dict | None = None

_VERSION_PRIORITY = ("v3-hardcoded", "v4-pro-host-filtered", "v1-minimal")

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection | None:
    global _conn
    if _conn is not None:
        return _conn
    try:
        if not Path(DB_PATH).exists():
            log.warning("noise_laws.db не найден по пути %s", DB_PATH)
            return None
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        return _conn
    except sqlite3.Error as e:
        log.warning("Ошибка открытия noise_laws.db: %s", e)
        return None


def get_law_for_region(region: str) -> dict | None:
    """Возвращает {"закон": ..., "уверенность": ..., "url": ...} или None."""
    if not region:
        return None

    conn = _get_conn()
    if conn is None:
        return None

    try:
        for version in _VERSION_PRIORITY:
            cur = conn.execute(
                "SELECT law_name, law_url, confidence FROM noise_laws "
                "WHERE region = ? AND prompt_version = ?",
                (region, version),
            )
            row = cur.fetchone()
            if row and row["law_name"] and row["law_name"] not in ("0", ""):
                return {
                    "закон": row["law_name"],
                    "уверенность": row["confidence"] or "",
                    "url": row["law_url"] or "",
                    "version": version,
                }
        return None
    except sqlite3.Error as e:
        log.warning("Ошибка чтения закона для %r: %s", region, e)
        return None

def get_article_for_region(region: str) -> str | None:
    """Читает статью про тишину из noise_articles.json.

    Returns: "Статья N. Название" или None.
    Загружается один раз, кэшируется.
    """
    global _articles_cache
    if _articles_cache is None:
        if not _ARTICLES_PATH.exists():
            log.info("noise_articles.json не найден: %s", _ARTICLES_PATH)
            _articles_cache = {}
        else:
            try:
                with open(_ARTICLES_PATH, "r", encoding="utf-8") as f:
                    _articles_cache = json.load(f)
                log.info("Загружено статей: %d", len(_articles_cache))
            except Exception as e:
                log.warning("Не удалось прочитать noise_articles.json: %s", e)
                _articles_cache = {}

    if not region:
        return None
    entry = _articles_cache.get(region)
    if not entry:
        return None
    art = entry.get("article")
    return art if art else None
