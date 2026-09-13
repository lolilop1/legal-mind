"""Справочник владельцев агрегаторов (маркетплейсов).

Реестр цифровых платформ Минэкономразвития (запуск 01.10.2026).
Юридически: покупка через маркетплейс — дистанционный способ
(ст. 26.1 ЗоЗПП). Ответственность распределяется:
- продавец-партнёр — за товар (ст. 18, 25)
- владелец агрегатора — за информацию и за возврат денег (ст. 12, 26.1)

Если поле пустое — значит данные ещё не подтверждены, дополнить позже.
"""

from __future__ import annotations


MARKETPLACES: dict[str, dict] = {
    "ozon": {
        "brand": "Ozon",
        "aliases": ("ozon", "озон"),
        "entity": "ООО \u00abИнтернет Решения\u00bb",
        "inn": "7704217370",
        "ogrn": "1027739244741",
        "address": "123112, г. Москва, Пресненская наб., д. 10",
    },
    "wildberries": {
        "brand": "Wildberries",
        "aliases": ("wildberries", "вайлдберриз", "wb", "вб"),
        "entity": "ООО \u00abРВБ\u00bb",
        "inn": "9714053621",
        "ogrn": "1247700471919",
        "address": "142181, Московская обл., г.о. Подольск, д. Коледино",
    },
    "yandex_market": {
        "brand": "Яндекс Маркет",
        "aliases": ("яндекс маркет", "яндекс.маркет", "yandex market", "ymarket"),
        "entity": "ООО \u00abЯндекс Маркет\u00bb",
        "inn": "9704254424",
        "ogrn": "1247700776850",
        "address": "119021, г. Москва, ул. Тимура Фрунзе, д. 11, к. 2",
    },
    "avito": {
        "brand": "Avito",
        "aliases": ("avito", "авито"),
        "entity": "ООО \u00abАвито\u00bb",
        "inn": "",
        "ogrn": "1117746802095",
        "address": "",
    },
    "lamoda": {
        "brand": "Lamoda",
        "aliases": ("lamoda", "ламода"),
        "entity": "ООО \u00abКупишуз\u00bb",
        "inn": "7705935687",
        "ogrn": "5107746007628",
        "address": "123308, г. Москва, пр-т Маршала Жукова, д. 1, стр. 1",
    },
    "yandex_eda": {
        "brand": "Яндекс Еда",
        "aliases": ("яндекс еда", "yandex eda", "eda.yandex"),
        "entity": "ООО \u00abЯндекс.Еда\u00bb",
        "inn": "9705114405",
        "ogrn": "1187746035730",
        "address": "115035, г. Москва, ул. Садовническая, д. 82, стр. 2",
    },
    "yandex_go": {
        "brand": "Яндекс Go",
        "aliases": ("яндекс go", "yandex go", "яндекс.го", "яндекс такси"),
        "entity": "ООО \u00abЯндекс.Такси\u00bb",
        "inn": "",
        "ogrn": "",
        "address": "",
    },
    "yandex_travel": {
        "brand": "Яндекс Путешествия",
        "aliases": ("яндекс путешествия", "yandex travel", "travel.yandex"),
        "entity": "ООО \u00abЯндекс.Вертикали\u00bb",
        "inn": "7704340327",
        "ogrn": "",
        "address": "",
    },
    "delivery_club": {
        "brand": "Delivery Club",
        "aliases": ("delivery club", "деливери клаб", "delivery-club"),
        "entity": "ООО \u00abДеливери Клаб\u00bb",
        "inn": "7705891253",
        "ogrn": "1097746360568",
        "address": "123112, г. Москва, 1-й Красногвардейский пр-д, д. 22, стр. 1",
    },
    "magnit_market": {
        "brand": "Магнит Маркет",
        "aliases": ("магнит маркет", "magnit market", "mm.ru"),
        "entity": "ООО \u00abМагнит Маркет\u00bb",
        "inn": "1648054022",
        "ogrn": "1211600048791",
        "address": "422550, Респ. Татарстан, г. Зеленодольск, ул. Ленина, д. 35",
    },
    "kuper": {
        "brand": "Купер",
        "aliases": ("купер", "kuper", "сбермаркет", "sbermarket"),
        "entity": "АО \u00abКупер\u00bb",
        "inn": "9724178764",
        "ogrn": "1247700135253",
        "address": "115230, г. Москва, пр-д Хлебозаводский, д. 7, стр. 9",
    },
    "joom": {
        "brand": "Joom",
        "aliases": ("joom", "джум"),
        "entity": "ООО \u00abДжум\u00bb",
        "inn": "7606124663",
        "ogrn": "1217600009494",
        "address": "150047, Ярославская обл., г. Ярославль",
    },
}


def resolve_marketplace(seller: str) -> dict | None:
    """Ищет маркетплейс по алиасам в строке продавца.

    Returns:
        {"key": "ozon", "brand": "Ozon", "entity": "...", ...} или None.
    """
    if not seller:
        return None
    s = seller.lower().strip()
    for key, data in MARKETPLACES.items():
        for alias in data["aliases"]:
            if alias in s:
                return {"key": key, **data}
    return None


def is_marketplace(seller: str) -> bool:
    return resolve_marketplace(seller) is not None


def all_aliases() -> tuple[str, ...]:
    """Плоский список всех алиасов — для hardchecks."""
    return tuple(
        alias
        for data in MARKETPLACES.values()
        for alias in data["aliases"]
    )
