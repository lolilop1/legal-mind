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
    check(len(RATES) == 6, f"RATES: 6 сценариев (получено {len(RATES)})")
    for sc in ("defect", "return14", "marketplace", "service",
               "delivery_delay", "repair_delay"):
        check(sc in RATES, f"RATES: {sc} есть")
    check(RATES["defect"]["rate_percent"] == 1.0, "RATES: defect 1%")
    check(RATES["service"]["rate_percent"] == 3.0, "RATES: service 3%")
    check(RATES["service"]["cap"] is True, "RATES: service cap=True")

    # ─── delivery_delay: 0.5%/день (ст. 23.1), cap = сумма предоплаты ───
    r_dd = calculate_penalty("delivery_delay", 50000, d, today=today)
    check(r_dd["applicable"] is True, "delivery: применимо")
    check(r_dd["rate_percent"] == 0.5, "delivery: ставка 0.5%")
    check(r_dd["amount"] == 7500.0,
          f"delivery: 7 500 за 30 дн. (получено {r_dd['amount']})")
    check(r_dd["capped"] is False, "delivery: cap не упёрся")
    check("23.1" in r_dd["law"], "delivery: норма ст. 23.1")

    today_very_long = _dt.date(2027, 3, 15)
    r_dd_cap = calculate_penalty("delivery_delay", 50000, d, today=today_very_long)
    check(r_dd_cap["amount"] == 50000.0,
          f"delivery: cap = 50 000 (получено {r_dd_cap['amount']})")
    check(r_dd_cap["capped"] is True, "delivery: capped=True")

    bc_dd = build_calculation(
        "marketplace",
        {"цена": "50000", "дата_обращения": "01.08.2026"},
        today=today,
        subtype="delivery_delay",
    )
    check(bc_dd is not None, "build delivery: не None")
    check(bc_dd["penalty"] == 7500.0, "build delivery: penalty 7500")
    check("23.1" in bc_dd["law"], "build delivery: law 23.1")

    bc_mp = build_calculation(
        "marketplace",
        {"цена": "50000", "дата_обращения": "01.08.2026"},
        today=today,
    )
    check(bc_mp is not None and bc_mp["penalty"] == 15000.0,
          "build marketplace без subtype: 1% (15000)")

    # ─── repair_delay: 1%/день, срок ремонта 45 дней (ст. 20, 23) ───
    d_repair = _dt.date(2026, 6, 1)
    today_r = _dt.date(2026, 9, 13)
    r_rep = calculate_penalty("repair_delay", 50000, d_repair, today=today_r)
    check(r_rep["applicable"] is True, "repair: применимо")
    check(r_rep["rate_percent"] == 1.0, "repair: ставка 1%")
    check(r_rep["days_overdue"] == 59,
          f"repair: 59 дней просрочки (получено {r_rep['days_overdue']})")
    check(r_rep["amount"] == 29500.0,
          f"repair: 29 500 (получено {r_rep['amount']})")
    check("20" in r_rep["law"] and "23" in r_rep["law"],
          "repair: нормы ст. 20, 23")
    check(r_rep["capped"] is False, "repair: cap не применяется")

    # build_calculation с subtype=repair_delay
    bc_rep = build_calculation(
        "defect",
        {"цена": "50000", "дата_обращения": "01.06.2026"},
        today=today_r,
        subtype="repair_delay",
    )
    check(bc_rep is not None, "build repair: не None")
    check(bc_rep["penalty"] == 29500.0, "build repair: penalty 29500")
    check("20" in bc_rep["law"], "build repair: law 20")

    # ─── Ст. 24: расчёт по текущей цене (если товар подорожал) ───
    bc_bump = build_calculation(
        "defect",
        {"цена": "30000", "текущая_цена": "40000",
         "дата_обращения": "01.08.2026"},
        today=today,
    )
    check(bc_bump is not None, "Ст. 24: подорожал — не None")
    check(bc_bump["base_amount"] == 40000.0,
          f"Ст. 24: base 40 000 (получено {bc_bump['base_amount']})")
    check(bc_bump.get("price_bumped") is True, "Ст. 24: bumped=True")
    check(bc_bump.get("original_price") == 30000.0,
          "Ст. 24: original=30 000")
    # today в файле = 2026-09-10, дедлайн = 11.08, просрочка 30 дн.
    # 30 × 40000 × 1% = 12000
    check(bc_bump["penalty"] == 12000.0,
          f"Ст. 24: penalty 12 000 (получено {bc_bump['penalty']})")

    # Без текущей цены
    bc_plain = build_calculation(
        "defect",
        {"цена": "30000", "дата_обращения": "01.08.2026"},
        today=today,
    )
    check(bc_plain.get("price_bumped") is None,
          "Ст. 24: без текущей цены — нет bumped")

    # Подешевел — берём цену покупки
    bc_down = build_calculation(
        "defect",
        {"цена": "40000", "текущая_цена": "30000",
         "дата_обращения": "01.08.2026"},
        today=today,
    )
    check(bc_down["base_amount"] == 40000.0,
          "Ст. 24: подешевел — base 40 000 (цена покупки)")
    check(bc_down.get("price_bumped") is None,
          "Ст. 24: подешевел — bumped нет")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
