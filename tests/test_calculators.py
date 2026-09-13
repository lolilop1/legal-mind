"""Тесты калькулятора неустойки."""

import _bootstrap  # noqa: F401

import datetime as _dt

from modules.consumer.calculators import (
    RATES,
    parse_date,
    parse_amount,
    calculate_penalty,
    build_calculation,
    format_rub,
)


def main():
    passed = 0
    failed = 0

    def check(cond, label):
        nonlocal passed, failed
        if cond:
            print(f"[PASS] {label}")
            passed += 1
        else:
            print(f"[FAIL] {label}")
            failed += 1

    # ─── parse_amount ───
    check(parse_amount("50000") == 50000.0, "amount: 50000")
    check(parse_amount("50 000") == 50000.0, "amount: пробел-разделитель")
    check(parse_amount("50 000,50") == 50000.5, "amount: запятая-десятичная")
    check(parse_amount("50000.5") == 50000.5, "amount: точка-десятичная")
    check(parse_amount("50000 руб") == 50000.0, "amount: с 'руб'")
    check(parse_amount("50 000 ₽") == 50000.0, "amount: с ₽")
    check(parse_amount("") is None, "amount: пусто → None")
    check(parse_amount(None) is None, "amount: None → None")
    check(parse_amount("-500") is None, "amount: отрицательное → None")
    check(parse_amount(50000) == 50000.0, "amount: int на входе")

    # ─── parse_date ───
    check(parse_date("01.08.2026") == _dt.date(2026, 8, 1), "date: DD.MM.YYYY")
    check(parse_date("5.8.26") == _dt.date(2026, 8, 5), "date: D.M.YY")
    check(parse_date("01-08-2026") == _dt.date(2026, 8, 1), "date: DD-MM-YYYY")
    check(parse_date("2026-08-01") == _dt.date(2026, 8, 1), "date: ISO")
    check(parse_date("") is None, "date: пусто → None")
    check(parse_date("не дата") is None, "date: мусор → None")

    # ─── defect: 1%/день, срок 10 дней ───
    d = _dt.date(2026, 8, 1)
    today = _dt.date(2026, 9, 10)
    r = calculate_penalty("defect", 50000, d, today=today)
    check(r["applicable"] is True, "defect: применимо")
    check(r["rate_percent"] == 1.0, "defect: ставка 1%")
    check(r["days_overdue"] == 30, f"defect: 30 дней (получено {r['days_overdue']})")
    check(r["amount"] == 15000.0, f"defect: 15 000 ₽ (получено {r['amount']})")
    check(r["capped"] is False, "defect: cap не применяется")
    check("11.08.2026" in r["reason"], "defect: дедлайн в reason")

    # ─── service: 3%/день, cap = цена услуги ───
    r2 = calculate_penalty("service", 30000, d, today=today)
    check(r2["applicable"] is True, "service: применимо")
    check(r2["rate_percent"] == 3.0, "service: ставка 3%")
    check(r2["amount"] == 27000.0, f"service: 27 000 ₽ (получено {r2['amount']})")
    check(r2["capped"] is False, "service: cap не упёрся (27к < 30к)")

    # service с cap: 40 дней просрочки
    today_long = _dt.date(2026, 9, 20)
    r2_long = calculate_penalty("service", 30000, d, today=today_long)
    check(r2_long["amount"] == 30000.0,
          f"service: capped на 30 000 (получено {r2_long['amount']})")
    check(r2_long["capped"] is True, "service: capped=True")

    # ─── срок не истёк ───
    r3 = calculate_penalty("defect", 50000, today - _dt.timedelta(days=5), today=today)
    check(r3["applicable"] is False, "срок не истёк: not applicable")
    check(r3["amount"] == 0.0, "срок не истёк: 0 ₽")
    check("ещё не истёк" in r3["reason"], "срок не истёк: reason")

    # ─── сумма не указана ───
    r4 = calculate_penalty("defect", 0, d, today=today)
    check(r4["applicable"] is False, "0 сумма: not applicable")

    # ─── неизвестный сценарий ───
    r5 = calculate_penalty("unknown", 50000, d, today=today)
    check(r5["applicable"] is False, "unknown: not applicable")

    # ─── format_rub ───
    check(format_rub(15000.0) == "15 000,00", f"fmt: 15 000,00 (получено {format_rub(15000.0)})")
    check(format_rub(1234.5) == "1 234,50", "fmt: 1 234,50")
    check(format_rub(None) == "—", "fmt: None → —")

    # ─── build_calculation: всё есть ───
    bc = build_calculation(
        "defect",
        {"цена": "50000", "дата_обращения": "01.08.2026"},
        today=today,
    )
    check(bc is not None, "build: не None когда всё есть")
    check(bc["penalty"] == 15000.0, "build: penalty 15000")
    check(bc["total"] == 65000.0, "build: total 65000")
    check(bc["base_amount"] == 50000.0, "build: base 50000")

    # ─── build_calculation: нечего считать ───
    check(build_calculation("defect", {}, today=today) is None,
          "build: пусто → None")
    check(build_calculation(
        "defect",
        {"цена": "50000"},
        today=today,
    ) is None, "build: только цена без даты → None")
    check(build_calculation(
        "defect",
        {"дата_обращения": "01.08.2026"},
        today=today,
    ) is None, "build: только дата без цены → None")

    # ─── build_calculation: срок не истёк → None ───
    check(build_calculation(
        "defect",
        {"цена": "50000", "дата_обращения": (today - _dt.timedelta(days=5)).strftime("%d.%m.%Y")},
        today=today,
    ) is None, "build: срок не истёк → None")

    # ─── RATES: все 4 сценария ───
    check(len(RATES) == 4, f"RATES: 4 сценария (получено {len(RATES)})")
    for sc in ("defect", "return14", "marketplace", "service"):
        check(sc in RATES, f"RATES: {sc} есть")
    check(RATES["defect"]["rate_percent"] == 1.0, "RATES: defect 1%")
    check(RATES["service"]["rate_percent"] == 3.0, "RATES: service 3%")
    check(RATES["service"]["cap"] is True, "RATES: service cap=True")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
