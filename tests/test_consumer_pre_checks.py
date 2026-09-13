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

    # ─── Кейс 5б: физлицо БЕЗ адреса и БЕЗ ссылки → critical ───
    r5b = run_consumer_pre_checks({
        "проблема": "купил телефон, сломался",
        "продавец": "Мария Петрова",
    })
    check(any("Адрес или ссылка" in k.label for k in r5b.missing_critical),
          "Кейс 5б: физлицо без адреса и без ссылки — critical")

    # ─── Кейс 5б2: физлицо со ссылкой (без адреса) → OK ───
    r5b2 = run_consumer_pre_checks({
        "проблема": "купил телефон, сломался",
        "продавец": "Мария Петрова",
        "ссылка_продавца": "https://www.avito.ru/user/12345",
    })
    check(not r5b2.is_blocked,
          "Кейс 5б2: физлицо со ссылкой — не блокируется")
    check(any("Ссылка на профиль" in k.label for k in r5b2.known),
          "Кейс 5б2: ссылка попала в known")

    # ─── Кейс 5в: ООО без адреса — адрес critical ───
    r5v = run_consumer_pre_checks({
        "проблема": "купил телефон, сломался",
        "продавец": "ООО «М.Видео»",
    })
    check(any("Адрес продавца" in k.label for k in r5v.missing_critical),
          "Кейс 5в: ООО — адрес в critical")

    # ─── Кейс 6: дата покупки не указана — опциональное ───
    r6 = run_consumer_pre_checks({
        "проблема": "купил смартфон, сломался",
        "продавец": "М.Видео",
        "адрес_продавца": "Москва",
    })
    check(not r6.is_blocked, "Кейс 6: без даты не блокируется")
    check(any("Дата" in k.label for k in r6.missing_optional),
          "Кейс 6: дата в optional")

    # ─── Кейс 7: marketplace (с номером заказа — не блокируется) ───
    r7 = run_consumer_pre_checks({
        "проблема": "заказал на Ozon кроссовки, не подошёл размер",
        "продавец": "Ozon",
        "адрес_продавца": "Москва",
        "номер_заказа": "12345678-1234",
    })
    check(not r7.is_blocked, "Кейс 7: marketplace с номером заказа — ок")
    check(any("Ответчик" in k.label and "Ozon" in (k.value or "")
              for k in r7.known),
          "Кейс 7: ответчик = Ozon (владелец агрегатора)")
    check(any("Номер заказа" in k.label for k in r7.known),
          "Кейс 7: номер заказа в known")

    # ─── Кейс 7б: marketplace без номера заказа — блокируется ───
    r7b = run_consumer_pre_checks({
        "проблема": "заказал на Ozon кроссовки, не подошёл размер",
        "продавец": "Ozon",
        "адрес_продавца": "Москва",
    })
    check(r7b.is_blocked, "Кейс 7б: marketplace без номера заказа — блок")
    check(any("Номер заказа" in c.label for c in r7b.missing_critical),
          "Кейс 7б: critical = Номер заказа")

    # ─── Кейс 8: defect + техсложный + >15 дней ───
    import datetime as _dt
    long_ago = (_dt.date.today() - _dt.timedelta(days=30)).strftime("%d.%m.%Y")
    r8 = run_consumer_pre_checks(
        {
            "проблема": "купил смартфон Samsung, экран перестал работать",
            "продавец": "М.Видео",
            "адрес_продавца": "Москва",
            "дата_покупки": long_ago,
        },
        scenario="defect",
    )
    check(not r8.is_blocked, "Кейс 8: >15 дней — не блокируется (это warning)")
    check(any("Срок с момента покупки" in k.label for k in r8.known),
          "Кейс 8: срок известен")
    check(any("Существенность недостатка" in k.label
              for k in r8.missing_optional),
          "Кейс 8: предупреждение про существенность")

    # ─── Кейс 9: defect + техсложный + <=15 дней ───
    recent = (_dt.date.today() - _dt.timedelta(days=5)).strftime("%d.%m.%Y")
    r9 = run_consumer_pre_checks(
        {
            "проблема": "купил смартфон Samsung, не включается",
            "продавец": "М.Видео",
            "адрес_продавца": "Москва",
            "дата_покупки": recent,
        },
        scenario="defect",
    )
    check(not r9.is_blocked, "Кейс 9: <=15 дней — не блокируется")
    check(any("в пределах 15" in (k.value or "")
              for k in r9.known if "Срок" in k.label),
          "Кейс 9: срок в пределах 15")
    check(not any("Существенность" in k.label
                  for k in r9.missing_optional),
          "Кейс 9: без предупреждения о существенности")

    # ─── Кейс 10: return14 + техсложный — 15-дневка не активна ───
    r10 = run_consumer_pre_checks(
        {
            "проблема": "купил смартфон, не понравился цвет",
            "продавец": "М.Видео",
            "адрес_продавца": "Москва",
            "дата_покупки": long_ago,
        },
        scenario="return14",
    )
    check(not any("Срок с момента покупки" in k.label
                  for k in r10.known),
          "Кейс 10: return14 — 15-дневка не срабатывает (только defect)")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
