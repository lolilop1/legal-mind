"""Калькуляторы для потребительских споров.

Неустойка по ЗоЗПП:
- ст. 23: 1% за каждый день просрочки от цены товара
  (для требований по ст. 18, 22 — возврат денег, замена, уценка)
- ст. 28 п.5: 3% за каждый день просрочки от цены работы/услуги,
  но не более общей цены заказа

Ограничения:
- размер неустойки не может превышать сумму основного требования
- расчёт идёт от даты истечения срока исполнения требования (10 дней
  для возврата денег и услуг — ст. 22, 31)
"""

from __future__ import annotations

import datetime as _dt


# Ставки и сроки по сценариям
RATES: dict[str, dict] = {
    # Просрочка гарантийного ремонта (ст. 20 п.1) — 1% за каждый
    # день свыше 45 дней (ст. 23)
    "repair_delay": {
        "rate_percent": 1.0,
        "deadline_days": 45,
        "law": "ст. 20, 23 ЗоЗПП",
        "cap": False,
    },
    # Просрочка доставки (ст. 23.1 п.3) — 0.5% от суммы предоплаты
    "delivery_delay": {
        "rate_percent": 0.5,
        "deadline_days": 10,
        "law": "ст. 23.1 ЗоЗПП",
        "cap": True,
    },
    "defect": {
        "rate_percent": 1.0,
        "deadline_days": 10,
        "law": "ст. 22, 23 ЗоЗПП",
        "cap": False,
    },
    "return14": {
        "rate_percent": 1.0,
        "deadline_days": 10,
        "law": "ст. 22, 23 ЗоЗПП",
        "cap": False,
    },
    "marketplace": {
        "rate_percent": 1.0,
        "deadline_days": 10,
        "law": "ст. 22, 23 ЗоЗПП",
        "cap": False,
    },
    "service": {
        "rate_percent": 3.0,
        "deadline_days": 10,
        "law": "ст. 28, 31 ЗоЗПП",
        "cap": True,
    },
}


def parse_date(raw: str) -> _dt.date | None:
    """Парсит дату из строки. Поддерживает DD.MM.YYYY, DD.MM.YY, DD-MM-YYYY и т.д."""
    if not raw:
        return None
    s = str(raw).strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d-%m-%Y", "%d-%m-%y",
                "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return _dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_amount(raw) -> float | None:
    """Парсит сумму из строки/числа. Возвращает float или None."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw) if raw > 0 else None
    s = str(raw).strip().replace(" ", "").replace("\u00a0", "")
    s = s.replace("руб", "").replace("₽", "").replace(",", ".")
    # Убираем лишние точки, оставляем одну
    parts = s.split(".")
    if len(parts) > 2:
        s = "".join(parts[:-1]) + "." + parts[-1]
    try:
        val = float(s)
        return val if val > 0 else None
    except (ValueError, TypeError):
        return None


def calculate_penalty(
    scenario: str,
    amount: float,
    demand_date: _dt.date,
    today: _dt.date | None = None,
) -> dict:
    """Считает неустойку по сценарию.

    Args:
        scenario: defect / return14 / marketplace / service
        amount: цена товара/услуги (база для расчёта)
        demand_date: дата, когда требование было предъявлено продавцу
        today: опционально, для тестов; по умолчанию — сегодня

    Returns:
        dict с полями:
        - applicable: bool — есть ли просрочка
        - reason: str — человеческое объяснение
        - amount: float — сумма неустойки (0 если not applicable)
        - rate_percent: float
        - days_overdue: int
        - deadline_date: date — когда истёк срок исполнения требования
        - law: str — нормы
        - capped: bool — упиралась ли в потолок (= цена услуги)
    """
    if today is None:
        today = _dt.date.today()

    rate_info = RATES.get(scenario)
    if not rate_info:
        return {
            "applicable": False,
            "reason": f"Сценарий {scenario!r} не поддерживает расчёт неустойки",
            "amount": 0.0,
            "rate_percent": 0.0,
            "days_overdue": 0,
            "deadline_date": None,
            "law": "",
            "capped": False,
        }

    if amount <= 0:
        return {
            "applicable": False,
            "reason": "Не указана цена товара/услуги — расчёт невозможен",
            "amount": 0.0,
            "rate_percent": rate_info["rate_percent"],
            "days_overdue": 0,
            "deadline_date": None,
            "law": rate_info["law"],
            "capped": False,
        }

    deadline_date = demand_date + _dt.timedelta(days=rate_info["deadline_days"])
    days_overdue = (today - deadline_date).days

    if days_overdue <= 0:
        return {
            "applicable": False,
            "reason": (
                f"Срок исполнения требования ({rate_info['deadline_days']} дней "
                f"с {demand_date.strftime('%d.%m.%Y')}) ещё не истёк — "
                f"истекает {deadline_date.strftime('%d.%m.%Y')}"
            ),
            "amount": 0.0,
            "rate_percent": rate_info["rate_percent"],
            "days_overdue": 0,
            "deadline_date": deadline_date,
            "law": rate_info["law"],
            "capped": False,
        }

    penalty = amount * (rate_info["rate_percent"] / 100.0) * days_overdue
    capped = False
    if rate_info["cap"] and penalty > amount:
        penalty = amount
        capped = True

    return {
        "applicable": True,
        "reason": (
            f"Просрочка {days_overdue} дн. с {deadline_date.strftime('%d.%m.%Y')} "
            f"по {today.strftime('%d.%m.%Y')}"
        ),
        "amount": round(penalty, 2),
        "rate_percent": rate_info["rate_percent"],
        "days_overdue": days_overdue,
        "deadline_date": deadline_date,
        "law": rate_info["law"],
        "capped": capped,
    }


def format_rub(value: float) -> str:
    """12345.67 -> '12 345,67'."""
    if value is None:
        return "—"
    s = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return s


def build_calculation(
    scenario: str,
    user_data: dict,
    today: _dt.date | None = None,
    subtype: str | None = None,
) -> dict | None:
    """Собирает расчёт из полей формы. None если считать нечего.

    Читает:
    - цена / сумма (если указана)
    - дата_обращения (когда требование предъявлено продавцу)

    Если subtype == "delivery_delay" — использует ставку 0.5% (ст. 23.1).
    """

    # Если подтип = просрочка доставки, работаем по ст. 23.1
    if subtype == "delivery_delay":
        scenario = "delivery_delay"
    # Просрочка ремонта — ст. 20 (45 дней)
    if subtype == "repair_delay":
        scenario = "repair_delay"

    amount = parse_amount(
        user_data.get("цена") or user_data.get("amount") or user_data.get("сумма")
    )
    demand_date = parse_date(
        user_data.get("дата_обращения") or user_data.get("дата_требования")
    )

    if amount is None or demand_date is None:
        return None

    result = calculate_penalty(scenario, amount, demand_date, today=today)
    if not result.get("applicable"):
        return None

    return {
        "base_amount": amount,
        "penalty": result["amount"],
        "total": round(amount + result["amount"], 2),
        "rate_percent": result["rate_percent"],
        "days_overdue": result["days_overdue"],
        "deadline_date": result["deadline_date"],
        "law": result["law"],
        "reason": result["reason"],
        "capped": result["capped"],
    }
