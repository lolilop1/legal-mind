# -*- coding: utf-8 -*-
"""Тесты категорий consumer'а."""

import _bootstrap  # noqa: F401

from modules.consumer.categories import (
    CATEGORIES, detect_category, get_category, all_codes
)


CASES = [
    ("купил смартфон Samsung", "smartphone"),
    ("айфон сломался через неделю", "smartphone"),
    ("ноутбук не включается", "laptop"),
    ("телевизор с трещиной на экране", "tv"),
    ("наушники не работают", "headphones"),
    ("холодильник не морозит", "fridge"),
    ("стиральная машина потекла", "washer"),
    ("пылесос сломался", "vacuum"),
    ("мультиварка не греет", "multicooker"),
    ("кофемашина не работает", "coffeemaker"),
    ("кондиционер не охлаждает", "ac"),
    ("куртка не подошла по размеру", "jacket"),
    ("пальто не понравилось", "coat"),
    ("платье не подошло", "dress"),
    ("джинсы не по размеру", "jeans"),
    ("рубашка маломерит", "shirt"),
    ("кроссовки не подошли", "sneakers"),
    ("диван неудобный", "sofa"),
    ("шкаф повредили при доставке", "wardrobe"),
    ("матрас не подошёл", "mattress"),
    ("духи не понравились", "perfume"),
    ("крем вызвал аллергию", "cosmetics"),
    ("молоко прокисло", "dairy"),
    ("мясо оказалось просроченным", "meat"),
    ("хлеб с плесенью", "bread"),
    ("детское питание просрочено", "baby_food"),
    ("лекарство не помогло", "medicine"),
    ("тонометр показывает неверно", "medical_device"),
    ("золотое кольцо сломалось", "jewelry"),
    ("детская коляска сломалась", "stroller"),
    ("автокресло не подошло", "car_seat"),
    ("игрушка сломалась", "toys"),
    ("велосипед с браком", "bike"),
    ("беговая дорожка сломалась", "fitness"),
    ("плитка треснула", "tile"),
    ("ламинат вздулся", "laminate"),
    ("обои отклеились", "wallpaper"),
    ("краска не того цвета", "paint"),
    ("дрель сломалась", "tools"),
    ("шины не подошли", "tires"),
    ("запчасть не подошла", "auto_parts"),
    ("аккумулятор сдох", "battery"),
    ("ремонт квартиры плохо сделали", "repair_flat"),
    ("автосервис накосячил", "repair_auto"),
    ("курсы английского не понравились", "education"),
    ("стоматолог сделал плохо", "medical_service"),
    ("тур оказался хуже", "tourism"),
    ("банк навязал страховку", "bank"),
    ("страховая не платит", "insurance"),
    ("юрист обманул", "legal"),
    ("доставка опоздала", "delivery"),
    ("стрижка испортили волосы", "manicure" if False else "beauty"),
    # None
    ("что-то не так", None),
    ("", None),
]


def main():
    passed = 0
    failed = 0

    # Проверка что все коды есть
    print(f"Категорий: {len(CATEGORIES)}\n")

    for text, expected in CASES:
        got = detect_category(text)
        ok = got == expected
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"[FAIL] {text!r:50} -> {got}  (ждём {expected})")

    # Проверка get_category
    cat = get_category("smartphone")
    if cat and cat.get("title") == "смартфона":
        passed += 1
    else:
        failed += 1
        print("[FAIL] get_category('smartphone')")

    if get_category("unknown") is None:
        passed += 1
    else:
        failed += 1
        print("[FAIL] get_category unknown -> None")

    # Проверка tech_complex
    if get_category("smartphone").get("tech_complex") is True:
        passed += 1
    else:
        failed += 1
        print("[FAIL] smartphone.tech_complex=True")

    if get_category("jacket").get("tech_complex") is False:
        passed += 1
    else:
        failed += 1
        print("[FAIL] jacket.tech_complex=False")

    # Все коды возвращаются
    codes = all_codes()
    if len(codes) == len(CATEGORIES):
        passed += 1
    else:
        failed += 1
        print("[FAIL] all_codes len")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
