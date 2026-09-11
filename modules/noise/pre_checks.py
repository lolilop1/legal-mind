"""Pre-checks для модуля 3 (Жалоба на шум)."""

from __future__ import annotations

import re

from core.pre_checks import (
    PreCheckReport,
    add_known,
    add_missing_critical,
    add_missing_optional,
)


_NOISE_TYPE_PATTERNS = [
    (r"музык", "Музыка"),
    (r"перфоратор", "Ремонт (перфоратор)"),
    (r"ремонт", "Ремонт"),
    (r"крич|орут|орет", "Крики"),
    (r"лай|лает|лают|собак", "Лай собаки"),
    (r"топот|топают|топает", "Топот"),
    (r"сверл", "Сверление"),
    (r"долб", "Долбёжка"),
    (r"грохоч", "Грохот"),
    (r"вечеринк|гулянк|пляс", "Вечеринки"),
    (r"скандал|дебош|драка|дерутся", "Скандалы, драки"),
    (r"пианин|гитар|барабан", "Музыкальные инструменты"),
]

_SOURCE_PATTERNS = [
    # Сначала конкретные направления — они информативнее общего "сосед"
    (r"сверху|этажом выше|надо мной", "Квартира сверху"),
    (r"снизу|этажом ниже|подо мной", "Квартира снизу"),
    (r"за стеной|за стенкой", "За стеной"),
    (r"из кв\.?\s*\d+|квартиры\s*№?\s*\d+|квартира\s*\d+", "Конкретная квартира"),
    # Общее — последним
    (r"сосед|соседк", "Сосед"),
]

_TIME_PATTERNS = [
    (r"ноч|в 3 ночи|в 2 ночи|в час ночи|после 22|после 23|после 0", "Ночное время"),
    (r"вечером|после 18|вечер", "Вечер"),
    (r"утром|с утра|до 8", "Утро"),
    (r"днём|днем|дневное", "День"),
]


def run_noise_pre_checks(user_data: dict, extras: dict | None = None) -> PreCheckReport:
    report = PreCheckReport()
    problem = (user_data.get("проблема") or "").strip()
    address = (user_data.get("адрес") or "").strip()
    date_started = (user_data.get("дата_начала") or "").strip()

    extras = extras or {}
    region = extras.get("region")
    law_data = extras.get("law_data")

    # Known
    add_known(report, "Тип проблемы", "Жалоба на нарушение тишины")
    if address:
        add_known(report, "Адрес", address)
    if region:
        add_known(report, "Регион", region)
    if law_data and law_data.get("закон"):
        add_known(report, "Применимый закон", law_data["закон"])
    if date_started:
        add_known(report, "Дата начала", date_started)

    # Вид шума
    noise_type = _match_first(problem, _NOISE_TYPE_PATTERNS)
    if noise_type:
        add_known(report, "Вид шума", noise_type)
    else:
        add_missing_critical(
            report,
            "Вид шума",
            "Не ясно, что именно слышно — музыка, ремонт, крики, "
            "лай собаки, топот и т.п.",
        )

    # Источник шума
    source = _match_first(problem, _SOURCE_PATTERNS)
    if source:
        add_known(report, "Источник шума", source)
    else:
        add_missing_critical(
            report,
            "Источник шума",
            "Укажите, кто шумит — сосед сверху, из квартиры № N, "
            "за стеной и т.п.",
        )

    # Время суток — опционально
    time_of_day = _match_first(problem, _TIME_PATTERNS)
    if time_of_day:
        add_known(report, "Время суток", time_of_day)
    else:
        add_missing_optional(
            report,
            "Время суток",
            "Когда именно — ночью, вечером. Усиливает жалобу.",
        )

    # Регион — опционально
    if not region:
        add_missing_optional(
            report,
            "Регион",
            "Не определён из адреса. В заявлении не будет ссылки на закон.",
        )

    return report


def _match_first(text: str, patterns: list[tuple[str, str]]) -> str | None:
    for pattern, label in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return label
    return None