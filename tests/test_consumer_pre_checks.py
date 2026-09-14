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

    # ─── Аудиотехника (магнитофон из тестерского кейса) ───
    r_audio = run_consumer_pre_checks(
        {
            "проблема": "Не работает магнитофон, не включается. Есть следы повреждений.",
            "продавец": "Ozon",
            "номер_заказа": "123456789-3030",
        },
        scenario="defect",
    )
    check(not r_audio.is_blocked,
          "аудио: магнитофон НЕ блокирует (тестерский кейс)")
    check(any("Аудио" in (k.value or "") for k in r_audio.known),
          "аудио: товар = Аудио/видео")
    check(not any("Товар" in c.label for c in r_audio.missing_critical),
          "аудио: 'Товар / услуга' НЕ в critical")

    # ─── Маркетплейс без адреса продавца — НЕ критично ───
    r_mp = run_consumer_pre_checks(
        {
            "проблема": "Купил смартфон на Ozon, пришёл с трещиной",
            "продавец": "Ozon",
            "номер_заказа": "12345-678",
        },
        scenario="defect",
    )
    check(not r_mp.is_blocked,
          "маркетплейс: без адреса продавца НЕ блокирует")
    check(any("Адрес продавца" in k.label for k in r_mp.known),
          "маркетплейс: адрес подставляется из справочника (known)")

    # ─── Avito (адрес пустой в справочнике) — тоже НЕ критично ───
    r_avito = run_consumer_pre_checks(
        {
            "проблема": "Купил телефон на Авито, оказался нерабочий",
            "продавец": "Avito",
            "номер_заказа": "нет",
        },
        scenario="defect",
    )
    check(not r_avito.is_blocked,
          "Avito: без адреса НЕ блокирует (адрес пуст в справочнике)")

    # ─── Обычное ООО без адреса — ДОЛЖНО блокировать ───
    r_ooo = run_consumer_pre_checks(
        {
            "проблема": "Купил смартфон в М.Видео, сломался",
            "продавец": "ООО «М.Видео»",
        },
        scenario="defect",
    )
    check(r_ooo.is_blocked,
          "ООО без адреса — блокирует (не сломали)")
    check(any("Адрес продавца" in c.label for c in r_ooo.missing_critical),
          "ООО без адреса — critical = Адрес продавца")

    # ─── Подтипы услуги (ст. 27-33) ───
    # 11: нарушен срок
    r11 = run_consumer_pre_checks(
        {
            "проблема": "заказал ремонт квартиры, обещали за 2 недели, "
                       "делают третий месяц, сроки нарушены",
            "продавец": "ООО РемСтрой",
            "адрес_продавца": "СПб",
        },
        scenario="service",
    )
    check(any("Подтип услуги" in k.label
              and "срок" in (k.value or "").lower()
              for k in r11.known),
          "Услуга 11: подтип = нарушен срок")

    # 12: смета превышена
    r12 = run_consumer_pre_checks(
        {
            "проблема": "заказал ремонт, сказали 50 тысяч, "
                       "в итоге требуют 120 тысяч, смету не согласовывали",
            "продавец": "ИП Иванов",
            "адрес_продавца": "Москва",
        },
        scenario="service",
    )
    check(any("Подтип услуги" in k.label
              and "смета" in (k.value or "").lower()
              for k in r12.known),
          "Услуга 12: подтип = смета превышена")

    # 13: отказ от услуги
    r13 = run_consumer_pre_checks(
        {
            "проблема": "оплатил курсы, передумал учиться, "
                       "хочу отказаться от услуги и вернуть деньги",
            "продавец": "ООО Учебный Центр",
            "адрес_продавца": "Москва",
        },
        scenario="service",
    )
    check(any("Подтип услуги" in k.label
              and "отказ" in (k.value or "").lower()
              for k in r13.known),
          "Услуга 13: подтип = отказ от услуги")

    # 14: некачественная работа
    r14 = run_consumer_pre_checks(
        {
            "проблема": "заказал ремонт квартиры, обои отклеиваются, "
                       "работа выполнена некачественно",
            "продавец": "ООО РемСтрой",
            "адрес_продавца": "СПб",
        },
        scenario="service",
    )
    check(any("Подтип услуги" in k.label
              and "некачествен" in (k.value or "").lower()
              for k in r14.known),
          "Услуга 14: подтип = некачественно")

    # 15: подтип НЕ детектится для defect (только service)
    r15 = run_consumer_pre_checks(
        {
            "проблема": "купил смартфон, сломался через неделю",
            "продавец": "М.Видео",
            "адрес_продавца": "Москва",
        },
        scenario="defect",
    )
    check(not any("Подтип услуги" in k.label for k in r15.known),
          "Услуга 15: подтип не для defect")

    # ─── Подтипы defect (отказ в ремонте, просрочка 45 дней) ───
    r16 = run_consumer_pre_checks(
        {
            "проблема": "отнёс смартфон в сервис, отказали в ремонте, "
                       "говорят не гарантийный случай",
            "продавец": "ООО «М.Видео»",
            "адрес_продавца": "Москва",
        },
        scenario="defect",
    )
    check(any("Подтип гарантийного случая" in k.label
              and "отказ" in (k.value or "").lower()
              for k in r16.known),
          "Defect 16: подтип = отказ в ремонте")

    r17 = run_consumer_pre_checks(
        {
            "проблема": "ремонт телефона длится уже третий месяц, "
                       "обещали за 2 недели",
            "продавец": "ООО «Сервис-Центр»",
            "адрес_продавца": "Москва",
        },
        scenario="defect",
    )
    check(any("Подтип гарантийного случая" in k.label
              and "просрочк" in (k.value or "").lower()
              for k in r17.known),
          "Defect 17: подтип = просрочка ремонта")

    r18 = run_consumer_pre_checks(
        {
            "проблема": "телефон перестал работать через месяц, хочу вернуть",
            "продавец": "ООО «М.Видео»",
            "адрес_продавца": "Москва",
        },
        scenario="defect",
    )
    # «недостат» без окончания — ловит «недостаток» и «недостатком»
    check(any("Подтип гарантийного случая" in k.label
              and "недостат" in (k.value or "").lower()
              for k in r18.known),
          "Defect 18: подтип = товар с недостатком")

    # подтип НЕ детектится для return14
    r19 = run_consumer_pre_checks(
        {
            "проблема": "купила куртку, не подошёл размер",
            "продавец": "ООО «Модный Магазин»",
            "адрес_продавца": "Москва",
        },
        scenario="return14",
    )
    check(not any("Подтип гарантийного случая" in k.label for k in r19.known),
          "Defect 19: подтип не для return14")

    # ─── Ст. 19: гарантия истекла, но 2 года не прошли ───
    r20 = run_consumer_pre_checks(
        {
            "проблема": "купил смартфон год назад, гарантия закончилась, сломался",
            "продавец": "ООО «М.Видео»",
            "адрес_продавца": "Москва",
        },
        scenario="defect",
    )
    check(any("Сроки предъявления" in k.label
              and "ст. 19" in (k.label or "")
              for k in r20.known),
          "Defect 20: гарантия истекла -> ст. 19 в known")
    check(any("Доказательство недостатка" in k.label
              for k in r20.missing_optional),
          "Defect 20: предупреждение про экспертизу")

    r21 = run_consumer_pre_checks(
        {
            "проблема": "купил вчера, не работает",
            "продавец": "ООО «М.Видео»",
            "адрес_продавца": "Москва",
        },
        scenario="defect",
    )
    check(not any("Сроки предъявления" in k.label for k in r21.known),
          "Defect 21: гарантия действует -> нет ст. 19")

    # ─── Ст. 16: ничтожные условия продавца ───
    for label, problem in [
        ("возврат невозможен", "купил телефон, магазин говорит возврат невозможен"),
        ("предоплата невозвратная", "продавец написал что предоплата невозвратная"),
        ("обмену не подлежит", "в чеке написано обмену и возврату не подлежит"),
        ("не принимает претензии", "магазин не принимает претензии"),
    ]:
        r = run_consumer_pre_checks(
            {"проблема": problem, "продавец": "ООО «Тест»", "адрес_продавца": "Москва"},
            scenario="defect",
        )
        check(any("Ничтожное условие" in k.label for k in r.known),
              f"Ст. 16: {label}")

    r_clean = run_consumer_pre_checks(
        {
            "проблема": "обычная ситуация, смартфон сломался",
            "продавец": "ООО «Тест»",
            "адрес_продавца": "Москва",
        },
        scenario="defect",
    )
    check(not any("Ничтожное условие" in k.label for k in r_clean.known),
          "Ст. 16: чистая ситуация -> нет условия")

    # ─── Специальные виды услуг (банк/страховка/туризм/образование/медицина) ───
    for label, problem in [
        ("банк", "взял кредит в банке, навязали страховку"),
        ("банк-комиссия", "банк скрыл комиссию при оформлении кредитной карты"),
        ("страховая", "страховая не выплачивает по ОСАГО"),
        ("туризм", "купил тур, отель оказался хуже чем в описании"),
        ("образование", "оплатил курс английского, не понравилось"),
        ("медицина", "стоматология сделала имплант, болит, переделывать не хотят"),
    ]:
        r = run_consumer_pre_checks(
            {
                "проблема": problem,
                "продавец": "ООО «Услуга»",
                "адрес_продавца": "Москва",
            },
            scenario="service",
        )
        check(any("Подтип услуги" in k.label for k in r.known),
              f"Service спец: {label}")

    r_bank = run_consumer_pre_checks(
        {
            "проблема": "взял кредит в банке, навязали страховку",
            "продавец": "ПАО Банк",
            "адрес_продавца": "Москва",
        },
        scenario="service",
    )
    check(any("Банковская" in (k.value or "") for k in r_bank.known
              if "Подтип услуги" in k.label),
          "Service спец: банк -> банковская услуга")

    # Нарушен срок (расширенный регекс)
    r_srok = run_consumer_pre_checks(
        {
            "проблема": "заказал ремонт квартиры, обещали за 2 недели, "
                       "делают третий месяц",
            "продавец": "ООО РемСтрой",
            "адрес_продавца": "Москва",
        },
        scenario="service",
    )
    check(any("Нарушен срок" in (k.value or "") for k in r_srok.known),
          "Service спец: обещали+делают -> нарушен срок")

    # ─── Ст. 10 (право на информацию) и ст. 12 (недостоверная) ───
    r30 = run_consumer_pre_checks(
        {
            "проблема": "продавец не сообщил, что товар невозвратный",
            "продавец": "ООО «Тест»",
            "адрес_продавца": "Москва",
        },
        scenario="defect",
    )
    check(any("Ст. 10" in k.label or "ст. 10" in (k.label or "")
              for k in r30.known),
          "Ст. 10: право на информацию")

    r31 = run_consumer_pre_checks(
        {
            "проблема": "на сайте было написано 256 ГБ, а пришло 128 ГБ",
            "продавец": "ООО «Тест»",
            "адрес_продавца": "Москва",
        },
        scenario="defect",
    )
    check(any("Ст. 12" in k.label or "ст. 12" in (k.label or "")
              for k in r31.known),
          "Ст. 12: недостоверная информация")

    r32 = run_consumer_pre_checks(
        {
            "проблема": "продавец ввёл в заблуждение о свойствах товара",
            "продавец": "ООО «Тест»",
            "адрес_продавца": "Москва",
        },
        scenario="defect",
    )
    check(any("Ст. 12" in k.label or "ст. 12" in (k.label or "")
              for k in r32.known),
          "Ст. 12: ввёл в заблуждение")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
