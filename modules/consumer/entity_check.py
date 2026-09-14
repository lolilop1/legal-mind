"""Entity check для модуля 1 (Потребитель).

Проверяет, что LLM не выдумала даты и цены: все значимые числа
в формальном описании должны присутствовать во входе.
"""
from __future__ import annotations

import re


# Даты: DD.MM.YYYY, DD.MM.YY, DD-MM-YYYY, DD/MM/YYYY
_DATE_RE = re.compile(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})\b")

# Цены: число рядом с маркером валюты / стоимости / цены
_PRICE_RES = (
    re.compile(r"(\d[\d\s\u00a0]*)\s*(?:руб|₽|рублей)", re.IGNORECASE),
    re.compile(r"стоимост[ьиюя][^\d]{0,20}?(\d[\d\s\u00a0]*)", re.IGNORECASE),
    re.compile(r"цен[аыуе][^\d]{0,20}?(\d[\d\s\u00a0]*)", re.IGNORECASE),
)

# Малые числа — это сроки из закона (3, 7, 10, 15, 20, 30, 45, 100…).
# Их не флагаем — они не «выдуманные данные», а нормы.
_SAFE_SMALL = set(range(1, 101))


def _normalize_date(d: str, mo: str, y: str) -> str:
    year = int(y)
    if year < 100:
        year += 2000
    return f"{int(d):02d}.{int(mo):02d}.{year:04d}"


def _extract_dates(text: str) -> set[str]:
    if not text:
        return set()
    out = set()
    for m in _DATE_RE.finditer(text):
        try:
            out.add(_normalize_date(*m.groups()))
        except (ValueError, TypeError):
            continue
    return out


def _extract_prices(text: str) -> set[str]:
    """Значимые цены: '5006 руб', 'стоимость 5006', 'цена 5006'."""
    if not text:
        return set()
    out = set()
    for pat in _PRICE_RES:
        for m in pat.finditer(text):
            num = m.group(1).replace(" ", "").replace("\u00a0", "").strip()
            if not num:
                continue
            try:
                v = float(num)
            except ValueError:
                continue
            if v in _SAFE_SMALL or v < 1000:
                continue
            out.add(f"{v:g}")
    return out


def _input_numbers(user_data: dict) -> set[str]:
    """Все числа из всех полей user_data (как строки)."""
    out = set()
    for v in user_data.values():
        if v is None:
            continue
        for m in re.finditer(r"\d+", str(v)):
            out.add(m.group(0))
    return out


def _input_dates(user_data: dict) -> set[str]:
    """Все даты из всех полей user_data."""
    out = set()
    for v in user_data.values():
        if v is None:
            continue
        out |= _extract_dates(str(v))
    return out


def check_consumer_numeric_recall(user_data: dict, formal_text: str) -> dict:
    """Возвращает {'ok': bool, 'missing': [...]}.

    missing = список {'kind': 'date'|'price', 'value': '...'}
    """
    if not formal_text:
        return {"ok": True, "missing": []}

    input_nums = _input_numbers(user_data)
    input_dates = _input_dates(user_data)

    missing = []

    # 1. Даты
    for d in sorted(_extract_dates(formal_text)):
        if d in input_dates:
            continue
        # Мягкий допуск: день и месяц встречаются во входе отдельно
        day, month, _ = d.split(".")
        if day in input_nums and month in input_nums:
            continue
        missing.append({"kind": "date", "value": d})

    # 2. Цены
    for p in sorted(_extract_prices(formal_text)):
        if p in input_nums:
            continue
        p_int = p.split(".")[0]
        if p_int in input_nums:
            continue
        missing.append({"kind": "price", "value": p})

    return {"ok": not missing, "missing": missing}
