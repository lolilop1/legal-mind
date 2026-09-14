# -*- coding: utf-8 -*-
"""Тесты entity_check для consumer: галлюцинации чисел и дат."""

import _bootstrap  # noqa: F401

from modules.consumer.entity_check import check_consumer_numeric_recall


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

    # ─── 1. Чистый случай: нечего флагать ───
    r = check_consumer_numeric_recall(
        {"проблема": "магнитофон не включается, купил вчера"},
        "Куплен магнитофон, не включается.",
    )
    check(r["ok"], "чистый текст — ok")
    check(not r["missing"], "чистый текст — пусто в missing")

    # ─── 2. Тестерский кейс: выдуманные дата и цена ───
    r = check_consumer_numeric_recall(
        {"проблема": "не работает магнитофон, не включается",
         "продавец": "Ozon", "номер_заказа": "123456789-3030"},
        "Куплен магнитофон стоимостью 5006 рублей 14.09.2026. Не включается.",
    )
    check(not r["ok"], "тестерский: не ok")
    kinds = {m["kind"] for m in r["missing"]}
    check("date" in kinds, "тестерский: дата в missing")
    check("price" in kinds, "тестерский: цена в missing")
    vals = {m["value"] for m in r["missing"]}
    check("14.09.2026" in vals, "тестерский: 14.09.2026 в missing")
    check("5006" in vals, "тестерский: 5006 в missing")

    # ─── 3. Дата ЕСТЬ во входе — не флагается ───
    r = check_consumer_numeric_recall(
        {"проблема": "купил 10.09.2026, сломался", "дата_покупки": "10.09.2026"},
        "Куплен товар 10.09.2026, выявлен недостаток.",
    )
    check(r["ok"], "дата есть во входе — ok")

    # ─── 4. Цена ЕСТЬ во входе — не флагается ───
    r = check_consumer_numeric_recall(
        {"проблема": "купил за 50000, сломался", "цена": "50000"},
        "Куплен товар стоимостью 50000 рублей.",
    )
    check(r["ok"], "цена есть во входе — ok")

    # ─── 5. Сроки из закона (45 дней, 10 дней) — НЕ флагаются ───
    r = check_consumer_numeric_recall(
        {"проблема": "сломался"},
        "Требовать в течение 10 дней, ремонт 45 дней, ст. 18.",
    )
    check(r["ok"], "сроки из закона не флагаются")

    # ─── 6. Малые числа (< 1000) — не флагаются ───
    r = check_consumer_numeric_recall(
        {"проблема": "сломался"},
        "Товар сломался в течение 3 дней, ст. 20, п. 5.",
    )
    check(r["ok"], "малые числа не флагаются")

    # ─── 7. Только цена без даты ───
    r = check_consumer_numeric_recall(
        {"проблема": "магнитофон сломался"},
        "Куплен магнитофон стоимостью 7000 рублей.",
    )
    check(not r["ok"], "только цена выдумана — не ok")
    check(len(r["missing"]) == 1 and r["missing"][0]["kind"] == "price",
          "только цена: одна missing, kind=price")

    # ─── 8. Только дата без цены ───
    r = check_consumer_numeric_recall(
        {"проблема": "магнитофон сломался"},
        "Куплен магнитофон 01.01.2026.",
    )
    check(not r["ok"], "только дата выдумана — не ok")
    check(len(r["missing"]) == 1 and r["missing"][0]["kind"] == "date",
          "только дата: одна missing, kind=date")

    # ─── 9. Пустой формальный текст — не падает ───
    r = check_consumer_numeric_recall({"проблема": "x"}, "")
    check(r["ok"], "пустой текст — ok (не падает)")

    # ─── 10. Дата в формате DD-MM-YYYY ───
    r = check_consumer_numeric_recall(
        {"проблема": "сломался"},
        "Куплен 14-09-2026.",
    )
    check(not r["ok"], "дата DD-MM-YYYY ловится")
    check(r["missing"][0]["value"] == "14.09.2026",
          "дата DD-MM-YYYY нормализована в DD.MM.YYYY")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
