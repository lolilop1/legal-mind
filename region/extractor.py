"""Extract federal subject (region) from a free-form Russian address.

Hybrid strategy:
1. Fast path: regex patterns.
2. Fallback: semantic search via Yandex AI Studio embeddings.
"""

from __future__ import annotations

import logging

from region.regex import _COMPILED as _REGEX_COMPILED


log = logging.getLogger("legal_mind")


def _extract_by_regex(address: str) -> str | None:
    if not address:
        return None

    normalized = address.strip()
    matches: list[tuple[str, int]] = []

    for region, pattern in _REGEX_COMPILED:
        m = pattern.search(normalized)
        if m:
            matches.append((region, m.end() - m.start()))

    if not matches:
        return None
    if len(matches) == 1:
        return matches[0][0]

    matches.sort(key=lambda x: -x[1])
    return matches[0][0]


def _extract_by_embeddings(address: str) -> str | None:
    try:
        from region.embeddings import search_region
        return search_region(address)
    except Exception as e:
        log.warning("Embedding search failed: %s", e)
        return None


def extract_region(address: str) -> str | None:
    region = _extract_by_regex(address)
    if region is not None:
        return region

    log.info("Regex не справился с %r, пробуем эмбеддинги", (address or "")[:60])
    return _extract_by_embeddings(address)