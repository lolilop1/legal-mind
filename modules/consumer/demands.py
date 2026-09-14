"""Универсальный справочник требований потребителя.

Один список на все 4 сценария. Юзер сам выбирает — сервис не угадывает.

Код → {label, wording, deadline_days, deadline_legal, applicable_scenarios}
"""

from __future__ import annotations


DEMANDS: dict[str, dict] = {
    "money": {
        "label": "Вернуть деньги за товар",
        "wording": "возвратить уплаченную за товар сумму",
        "deadline_days": 10,
        "deadline_legal": "ст. 22 ЗоЗПП",
        "applicable": ("defect", "return14", "marketplace", "service"),
    },
    "replace": {
        "label": "Заменить товар на аналогичный",
        "wording": "заменить товар на аналогичный",
        "deadline_days": 7,
        "deadline_legal": "ст. 21 ЗоЗПП",
        "applicable": ("defect", "marketplace"),
    },
    "exchange": {
        "label": "Обменять на другой размер/цвет",
        "wording": "обменять товар на аналогичный товар другого размера, "
                   "формы, габарита, фасона, расцветки или комплектации",
        "deadline_days": 7,
        "deadline_legal": "ст. 25 ЗоЗПП",
        "applicable": ("return14",),
    },
    "repair": {
        "label": "Безвозмездно отремонтировать",
        "wording": "безвозмездно устранить недостатки товара",
        "deadline_days": 45,
        "deadline_legal": "ст. 20 ЗоЗПП",
        "applicable": ("defect", "marketplace"),
    },
    "discount": {
        "label": "Уменьшить цену (уценка)",
        "wording": "соразмерно уменьшить покупную цену товара",
        "deadline_days": 10,
        "deadline_legal": "ст. 22 ЗоЗПП",
        "applicable": ("defect", "return14", "marketplace", "service"),
    },
    "penalty": {
        "label": "Взыскать неустойку за просрочку",
        "wording": "уплатить неустойку за нарушение срока исполнения "
                   "требования",
        "deadline_days": 10,
        "deadline_legal": "ст. 22, 23 ЗоЗПП",
        "applicable": ("defect", "marketplace", "service"),
    },
    "refuse": {
        "label": "Отказаться от услуги и вернуть деньги",
        "wording": "отказаться от исполнения договора и возвратить "
                   "уплаченную сумму за вычетом фактически понесённых "
                   "исполнителем расходов",
        "deadline_days": 10,
        "deadline_legal": "ст. 31, 32 ЗоЗПП",
        "applicable": ("service",),
    },
    "fix_free": {
        "label": "Устранить недостатки услуги бесплатно",
        "wording": "безвозмездно устранить недостатки оказанной услуги",
        "deadline_days": 20,
        "deadline_legal": "ст. 30 ЗоЗПП",
        "applicable": ("service",),
    },
    "delivery_refund": {
        "label": "Вернуть предоплату (не доставили)",
        "wording": "возвратить сумму предварительной оплаты в связи "
                   "с нарушением срока передачи товара",
        "deadline_days": 10,
        "deadline_legal": "ст. 23.1 ЗоЗПП",
        "applicable": ("marketplace",),
    },
}


# Порядок для UI (сначала «деньги», они чаще всего)
_DEMAND_ORDER = (
    "money", "replace", "exchange", "repair",
    "discount", "penalty", "refuse", "fix_free", "delivery_refund",
)


def get_demand(code: str) -> dict | None:
    """Возвращает требование по коду с полями label/wording/deadline."""
    if not code:
        return None
    d = DEMANDS.get(code)
    if not d:
        return None
    return {"code": code, **d}


def list_for_scenario(scenario: str) -> list[dict]:
    """Возвращает все требования, применимые к сценарию, в UI-порядке."""
    if not scenario:
        return []
    out = []
    for code in _DEMAND_ORDER:
        d = DEMANDS.get(code)
        if d and scenario in d.get("applicable", ()):
            out.append({"code": code, **d})
    return out


def all_codes() -> list[str]:
    return list(_DEMAND_ORDER)
