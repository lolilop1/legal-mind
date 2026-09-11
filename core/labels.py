"""Человекочитаемые названия для кодов системы.

В БД храним короткие коды (uk / noise / consumer / zayavlenie),
показываем пользователю по-русски.
"""

from __future__ import annotations


PROBLEM_TYPE_LABELS: dict[str, str] = {
    "uk":       "Жалоба в УК",
    "noise":    "Жалоба на шум",
    "consumer": "Защита прав потребителя",
}


DOC_TYPE_LABELS: dict[str, str] = {
    "zayavlenie": "Заявление",
    "claim":      "Претензия",
    "lawsuit":    "Иск",
    "complaint":  "Жалоба",
    "calc":       "Расчёт",
    "response":   "Ответ на претензию",
}


def problem_type_label(code: str | None) -> str:
    """'noise' -> 'Жалоба на шум'. Если нет — вернуть код."""
    if not code:
        return "—"
    return PROBLEM_TYPE_LABELS.get(code, code)


def doc_type_label(code: str | None) -> str:
    """'zayavlenie' -> 'Заявление'."""
    if not code:
        return "—"
    return DOC_TYPE_LABELS.get(code, code)