"""Legal Mind — Module 2: entity recall check.

After the LLM normalizes the user's problem into a formal description, this
module verifies that no legally significant entity from the source was lost.

It is a cheap deterministic gate, not a semantic comparator. It catches the
class of bug where the model silently drops a fact (e.g. "посторонние"
disappearing from a broken-intercom complaint) — a real risk for a legal
product, because the final document would be formally correct but legally
weaker.
"""

from __future__ import annotations

import re
from typing import Iterable


# Legal-significant markers. If a marker is present in the source, the formal
# description must contain it or one of its allowed synonyms.
SIGNIFICANT_MARKERS: dict[str, tuple[str, ...]] = {
    "посторонние":   ("посторонн", "незнаком", "чужих людей", "чужие люди"),
    "дети":          ("дет", "ребен", "ребён"),
    "инвалид":       ("инвалид", "маломобильн"),
    "пенсионер":     ("пенсионер", "пожил"),
    "газ":           ("газ",),
    "пожар":         ("пожар", "возгора", "горение"),
    "затопление":    ("затопл", "заливает", "залило"),
    "проводка":      ("проводк", "электропровод"),
    "несущая":       ("несущ",),
    "домофон":       ("домофон",),
    "лифт":          ("лифт",),
    "отопление":     ("отоплен", "батаре", "радиатор"),
    "крыша":         ("крыш", "кровл"),
    "подвал":        ("подвал", "подвальн"),
    "мусор":         ("мусор", "отход", "гряз"),
    "снег":          ("снег", "налед", "гололёд", "гололед"),
    "угрозы":        ("убива", "убийств", "избива", "напада", "угрожа", "расправ", "граб"),
    "биоотходы":     ("биологическ", "фекал", "испражнен", "обоссан", "насрал", "моча"),
    "драка":         ("драк", "дебош", "скандал"),
    "пьянство":      ("пьян", "спиртн", "алкогол"),
}


# Apartment numbers only — floor counts and day counts are too noisy and are
# often spelled out ("пять дней" vs "5 дней"), which would cause false alarms.
_APARTMENT_RE = re.compile(
    r"(?:№|кв\.?|квартир[аыуе]|квартиры)\s*(\d{1,4})",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"\b(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})\b")


def _norm(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _extract_apartments(text: str) -> set[str]:
    return set(_APARTMENT_RE.findall(text))


def _extract_dates(text: str) -> set[str]:
    return set(_DATE_RE.findall(text))


def _find_marker(text: str, forms: Iterable[str]) -> bool:
    return any(form in text for form in forms)


def check_entity_recall(
    source_problem: str,
    date_started: str,
    formal_description: str,
) -> dict:
    """Return {"ok": bool, "missing": [...]}

    missing is a list of dicts: {"kind": "marker"|"apartment"|"date",
    "value": str}
    """
    src = _norm(source_problem)
    dst = _norm(formal_description)
    date_src = _norm(date_started)

    missing: list[dict] = []

    # 1. Legal-significant markers.
    for canonical, forms in SIGNIFICANT_MARKERS.items():
        if _find_marker(src, forms) and not _find_marker(dst, forms):
            missing.append({"kind": "marker", "value": canonical})

    # 2. Apartment numbers (source -> output).
    for n in sorted(_extract_apartments(src) - _extract_apartments(dst)):
        missing.append({"kind": "apartment", "value": n})

    # 3. Dates from дата_начала must appear in the output.
    for d in sorted(_extract_dates(date_src)):
        if d not in dst:
            missing.append({"kind": "date", "value": d})

    return {"ok": not missing, "missing": missing}