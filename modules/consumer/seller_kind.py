"""Определение типа продавца (юрлицо / ИП / физлицо / маркетплейс).

Единая точка правды. Используется в:
- modules/consumer/hardchecks.py (проверка адреса продавца)
- modules/consumer/pre_checks.py (known «Ответчик»)

ВАЖНО: аналогичная логика есть в web/templates/index.html (функция
lmIsLegalEntity). При правке обновляй ОБА места — синхронизировано
вручную, потому что JS в браузере Python-код не вызовет.
"""

from __future__ import annotations

from modules.consumer.marketplaces import resolve_marketplace


LEGAL_PREFIXES: tuple[str, ...] = (
    "ООО", "АО", "ПАО", "ЗАО", "ОАО", "НКО",
    "МУП", "ГУП", "ТСЖ", "ТД", "ТЦ",
)


def is_marketplace(seller: str) -> bool:
    """True если продавец — известный маркетплейс."""
    return resolve_marketplace(seller) is not None


def is_legal_entity(seller: str) -> bool:
    """True если продавец — организация, ИП, самозанятый или маркетплейс.

    Для таких продавцов адрес обязателен (кроме маркетплейсов — там
    адрес подставляется автоматически из справочника).
    """
    s = (seller or "").strip()
    if not s:
        return True  # пусто → консервативно требуем адрес

    upper = s.upper()
    for prefix in LEGAL_PREFIXES:
        if upper.startswith(prefix + " ") or upper.startswith(prefix + "."):
            return True

    if upper.startswith("ИП ") or upper.startswith("ИП."):
        return True

    if "самозанят" in s.lower():
        return True

    if is_marketplace(s):
        return True

    return False