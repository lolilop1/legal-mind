"""Offline regression for Module 1 (consumer) hard checks. No API calls."""

import _bootstrap  # noqa: F401

from modules.consumer.hardchecks import hard_pre_check


BASE = {
    "продавец": "ООО «М.Видео»",
    "адрес_продавца": "125167, г. Москва, Ленинградский пр-т, д. 76А",
}


def check(problem, expected, label, overrides=None):
    data = dict(BASE)
    data["проблема"] = problem
    if overrides:
        data.update(overrides)
    r = hard_pre_check(data)

    if expected == "OK":
        ok = r is None
    elif expected == "STOP":
        ok = r is not None and r["stop"]
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

        # ─── STOP: нет адреса продавца ───
        ("купил смартфон, сломался, хочу вернуть",
         "STOP", "no seller address", {"адрес_продавца": ""}),
    ]

    results = [check(*t) for t in tests]

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
