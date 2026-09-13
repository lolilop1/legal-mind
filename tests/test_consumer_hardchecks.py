"""Offline regression for Module 1 (consumer) hard checks. No API calls."""

import _bootstrap  # noqa: F401

from modules.consumer.hardchecks import hard_pre_check


BASE = {
    "продавец": "ООО «М.Видео»",
    "адрес_продавца": "125167, г. Москва, Ленинградский пр-т, д. 76А",
}


def check(problem, expected, label, overrides=None, scenario=None):
    data = dict(BASE)
    data["проблема"] = problem
    if overrides:
        data.update(overrides)
    r = hard_pre_check(data, scenario=scenario)

    if expected == "OK":
        ok = r is None
    elif expected == "STOP":
        ok = r is not None and r["stop"]
    elif expected == "STOP_NONRET":
        ok = (r is not None and r.get("stop") is True
              and r.get("category") == "non_returnable")
    else:
        raise ValueError(expected)

    return {"label": label, "ok": ok, "expected": expected, "result": r}


def main():
    tests = [
        # ─── OK: типовые потребительские споры ───
        ("купил смартфон, перестал работать через неделю, хочу вернуть",
         "OK", "defect: смартфон сломался"),
        ("заказал на Ozon кроссовки, не подошёл размер",
         "OK", "marketplace: Ozon"),
        ("приобрела куртку в магазине, не понравился цвет, хочу обменять",
         "OK", "return14: не подошло"),
        ("оплатил ремонт квартиры, обои отклеиваются, переделывать не хотят",
         "OK", "service: ремонт"),
        ("купил телевизор в М.Видео, брак, продавец отказывает в возврате",
         "OK", "defect: телевизор"),
        ("покупка через Wildberries, товар сломан, не возвращают деньги",
         "OK", "marketplace: WB"),

        # ─── STOP: слишком короткие ───
        ("плохо", "STOP", "short: 5 символов — реальный short"),
        # 11 символов — проходит порог, это не short. Ожидаем OK (LLM разберётся).
        ("не работает пожалуйста помогите", "OK", "не короткое, но без маркеров покупки → уже не пройдёт"),

        # ─── STOP: только цифры/эмодзи ───
        ("12345 67890", "STOP", "digits only"),
        ("😡😡😡🗑️🗑️", "STOP", "emoji only"),

        # ─── STOP: явно соседи/шум ───
        ("соседи шумят ночью, музыка, не дают спать",
         "STOP", "routing: соседи → noise"),
        ("сосед сверху топает каждый вечер",
         "STOP", "routing: сосед сверху"),

        # ─── STOP: явно УК ───
        ("в подъезде не убирают две недели, грязь и мусор",
         "STOP", "routing: УК уборка"),
        ("батареи холодные, дома холодно",
         "STOP", "routing: УК отопление"),
        ("управляющая компания не реагирует на заявки",
         "STOP", "routing: УК явно"),

        # ─── STOP: нет маркеров покупки ───
        ("не знаю что делать, всё плохо, помогите пожалуйста",
         "STOP", "no purchase markers"),

        # ─── STOP: нет продавца ───
        ("купил смартфон, сломался, хочу вернуть",
         "STOP", "no seller", {"продавец": ""}),

        # ─── STOP_NONRET: невозвратные товары в return14 (Пост. 2463) ───
        ("купила трусы, не подошёл размер, хочу вернуть",
         "STOP_NONRET", "невращ: трусы + return14",
         None, "return14"),
        ("купил лекарство, не подошло, хочу вернуть",
         "STOP_NONRET", "невращ: лекарство + return14",
         None, "return14"),
        ("купила золотое кольцо, не понравилось, хочу вернуть",
         "STOP_NONRET", "невращ: ювелирка + return14",
         None, "return14"),
        ("купила зубную щетку, не подошла",
         "STOP_NONRET", "невращ: зубная щётка + return14",
         None, "return14"),
        ("купил носки, не подошли по размеру",
         "STOP_NONRET", "невращ: носки + return14",
         None, "return14"),
        ("купила духи, не понравился запах",
         "STOP_NONRET", "невращ: духи + return14",
         None, "return14"),
        ("купил книгу, не понравилась",
         "STOP_NONRET", "невращ: книга + return14",
         None, "return14"),
        ("купил саженцы яблони, не прижились",
         "STOP_NONRET", "невращ: саженцы + return14",
         None, "return14"),

        # ─── return14: обычные товары (НЕ блокируем) ───
        ("купила куртку, не подошёл размер",
         "OK", "return14: куртка — ок",
         None, "return14"),
        ("купил кроссовки, не подошли по цвету",
         "OK", "return14: кроссовки — ок",
         None, "return14"),
        ("купила платье, не подошло",
         "OK", "return14: платье — ок",
         None, "return14"),

        # ─── defect: невозвратные НЕ блокируем (ст. 18 работает) ───
        ("купил лекарство, оно оказалось бракованным",
         "OK", "невращ: лекарство + defect — ок (ст. 18)",
         None, "defect"),
        ("купила золотое кольцо, сломалось через день",
         "OK", "невращ: ювелирка + defect — ок (ст. 18)",
         None, "defect"),
        ("купил носки, порвались после первой носки",
         "OK", "невращ: носки + defect — ок (ст. 18)",
         None, "defect"),

        # ─── Без scenario — старые кейсы не ломаются ───
        ("купила трусы, не подошёл размер, хочу вернуть",
         "OK", "невращ: трусы без scenario — ок (legacy)"),

        # ─── Техсложные товары (Пост. 924) ───
        # return14 + техсложный → STOP_NONRET
        ("купил смартфон, не понравился цвет, хочу вернуть",
         "STOP_NONRET", "техсложный: смартфон + return14",
         None, "return14"),
        ("купила ноутбук, не подошёл, хочу сдать",
         "STOP_NONRET", "техсложный: ноутбук + return14",
         None, "return14"),
        ("купил холодильник, не понравился, хочу обменять",
         "STOP_NONRET", "техсложный: холодильник + return14",
         None, "return14"),
        ("купила телевизор, не подошёл по размеру",
         "STOP_NONRET", "техсложный: телевизор + return14",
         None, "return14"),
        ("купил диван, не подошёл по цвету",
         "STOP_NONRET", "техсложный: диван + return14",
         None, "return14"),
        ("купил айфон, не понравился, хочу вернуть",
         "STOP_NONRET", "техсложный: айфон + return14",
         None, "return14"),

        # defect + техсложный → OK (ст. 18 работает)
        ("купил смартфон, перестал работать через неделю",
         "OK", "техсложный: смартфон + defect — ок",
         None, "defect"),
        ("купила ноутбук, не включается",
         "OK", "техсложный: ноутбук + defect — ок",
         None, "defect"),
        ("купил холодильник, не морозит",
         "OK", "техсложный: холодильник + defect — ок",
         None, "defect"),
        ("телевизор сломался через месяц",
         "OK", "техсложный: телевизор + defect — ок",
         None, "defect"),

        # ─── STOP: нет адреса продавца ───
        ("купил смартфон, сломался, хочу вернуть",
         "STOP", "no seller address", {"адрес_продавца": ""}),
    ]

    results = []
    for t in tests:
        if len(t) == 5:
            results.append(check(t[0], t[1], t[2], t[3], t[4]))
        else:
            results.append(check(*t))

    passed = sum(bool(r["ok"]) for r in results)
    failed = len(results) - passed
    for r in results:
        status = "PASS" if r["ok"] else "FAIL"
        print(f"[{status}] {r['label']}")
        if not r["ok"]:
            print(f"       input: {r['result']}")
    print(f"\nTotal: {len(results)}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
