"""Offline tests for Module 1 (consumer) pre-checks. No API calls."""

import _bootstrap  # noqa: F401

from modules.consumer.pre_checks import run_consumer_pre_checks


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

    # ─── Кейс 1: всё на месте ───
    r1 = run_consumer_pre_checks({
        "проблема": "купил смартфон Samsung, перестал работать через неделю",
        "продавец": "ООО «М.Видео»",
        "адрес_продавца": "125167, Москва",
        "дата_покупки": "10.09.2026",
    })
    check(not r1.is_blocked, "Кейс 1: не блокируется")
    check(any("Электроника" in (k.value or "") for k in r1.known),
          "Кейс 1: товар = Электроника")
    check(any("неисправен" in (k.value or "") for k in r1.known),
          "Кейс 1: суть = неисправен")

    # ─── Кейс 2: нет товара ───
    r2 = run_consumer_pre_checks({
        "проблема": "что-то не так",
        "продавец": "Ozon",
        "адрес_продавца": "Москва",
    })
    check(r2.is_blocked, "Кейс 2: блокируется (нет товара)")
    check(any("Товар" in k.label for k in r2.missing_critical),
          "Кейс 2: critical = Товар")

    # ─── Кейс 3: кривой текст с опечатками (fallback) ───
    r3 = run_consumer_pre_checks({
        "проблема": "10 сентября купил самсунг а57, день прорабьотал слмоался. продавец забил болт",
        "продавец": "М.Видео",
        "адрес_продавца": "Москва",
    })
    check(not r3.is_blocked,
          "Кейс 3: кривой текст НЕ блокируется (fallback)")
    _sut = [k.value for k in r3.known if "Суть" in k.label]
    check(bool(_sut), "Кейс 3: суть распознана (fallback или regex)")
    print(f"       → суть = {_sut[0] if _sut else '—'}")

    # ─── Кейс 4: услуга ───
    r4 = run_consumer_pre_checks({
        "проблема": "заказал ремонт квартиры, плохо выполнили работу",
        "продавец": "ООО РемСтрой",
        "адрес_продавца": "СПб",
    })
    check(not r4.is_blocked, "Кейс 4: услуга не блокируется")
    check(any("Ремонт" in (k.value or "") or "услуг" in (k.value or "").lower()
              for k in r4.known),
          "Кейс 4: товар/услуга распознаны")

    # ─── Кейс 5а: нет продавца (адрес есть) ───
    r5a = run_consumer_pre_checks({
        "проблема": "купил телефон, сломался",
        "адрес_продавца": "Москва",
    })
    check(any("Продавец" in k.label for k in r5a.missing_critical),
          "Кейс 5а: critical = Продавец")
    check(not any("Адрес продавца" in k.label for k in r5a.missing_critical),
          "Кейс 5а: адрес продавца НЕ в critical (он передан)")

    # ─── Кейс 5б: продавец есть, адреса нет ───
    r5b = run_consumer_pre_checks({
        "проблема": "купил телефон, сломался",
        "продавец": "М.Видео",
    })
    check(any("Адрес продавца" in k.label for k in r5b.missing_critical),
          "Кейс 5б: critical = Адрес продавца")

    # ─── Кейс 6: дата покупки не указана — опциональное ───
    r6 = run_consumer_pre_checks({
        "проблема": "купил смартфон, сломался",
        "продавец": "М.Видео",
        "адрес_продавца": "Москва",
    })
    check(not r6.is_blocked, "Кейс 6: без даты не блокируется")
    check(any("Дата" in k.label for k in r6.missing_optional),
          "Кейс 6: дата в optional")

    # ─── Кейс 7: marketplace ───
    r7 = run_consumer_pre_checks({
        "проблема": "заказал на Ozon кроссовки, не подошёл размер",
        "продавец": "Ozon",
        "адрес_продавца": "Москва",
    })
    check(not r7.is_blocked, "Кейс 7: marketplace не блокируется")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
