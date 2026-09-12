"""Offline tests for consumer scenario detection. No API calls."""

import _bootstrap  # noqa: F401

from modules.consumer.scenario_detect import detect_scenario


CASES = [
    # marketplace
    ("купил смартфон на Ozon, сломался", "marketplace"),
    ("заказал на wildberries телефон, не подошёл по размеру", "marketplace"),
    ("покупка через Авито, продавец пропал", "marketplace"),
    ("заказал на Яндекс Маркет, товар не пришёл", "marketplace"),

    # service
    ("заказал ремонт квартиры, плохо сделали", "service"),
    ("платное обучение, курсы некачественные", "service"),
    ("стрижка в салоне испортили волосы", "service"),
    ("юрист не оказал услугу", "service"),
    ("доставка опоздала на неделю", "service"),
    ("косметолог навредил коже", "service"),

    # return14
    ("купил куртку, не подошёл размер", "return14"),
    ("не подошёл размер", "return14"),
    ("джинсы не по размеру, хочу вернуть", "return14"),
    ("ботинки не подошли по цвету", "return14"),
    ("платье не подошло", "return14"),
    ("не понравился цвет, хочу обменять", "return14"),
    ("маломерит на 2 размера", "return14"),

    # defect
    ("смартфон перестал работать через неделю", "defect"),
    ("приобрёл диван, брак", "defect"),
    ("купил телефон, перестал включаться", "defect"),
    ("ноутбук не включается", "defect"),
    ("холодильник сломался через месяц", "defect"),
    ("телевизор вышел из строя", "defect"),
    ("товар неисправен", "defect"),

    # не уверен
    ("что-то не так", None),
    ("плохо", None),
    ("", None),
]


def main():
    passed = 0
    failed = 0
    for problem, expected in CASES:
        got = detect_scenario(problem)
        ok = got == expected
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] {problem!r:60} → {got!r}  (ожидалось {expected!r})")

    print(f"\nTotal: {len(CASES)}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
