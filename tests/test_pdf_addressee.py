# -*- coding: utf-8 -*-
"""Тесты _format_addressee (умная шапка PDF) — все ветки."""

import _bootstrap  # noqa: F401

from modules.consumer.pdf import _format_addressee


def main():
    passed = 0
    failed = 0

    def check(cond, label, got=None):
        nonlocal passed, failed
        if cond:
            print(f"[PASS] {label}")
            passed += 1
        else:
            print(f"[FAIL] {label}")
            if got is not None:
                print(f"       got: {got!r}")
            failed += 1

    # ═══ 1. ООО / АО / ПАО → «Директору ...» ═══
    r = _format_addressee("ООО «М.Видео»")
    check(r.startswith("Директору") and "М.Видео" in r, "ООО «X» → Директору", r)

    r = _format_addressee("АО Ромашка")
    check(r.startswith("Директору") and "Ромашка" in r, "АО X → Директору", r)

    r = _format_addressee("ПАО Газпром")
    check(r.startswith("Директору") and "Газпром" in r, "ПАО X → Директору", r)

    r = _format_addressee("ООО Хендерсен")
    check("«Хендерсен»" in r, "ООО без кавычек → кавычки добавляются", r)

    r = _format_addressee("ООО «Хендерсен»")
    check("«Хендерсен»" in r and "««" not in r,
          "ООО с кавычками → не дублируются", r)

    # ═══ 2. ИП / самозанятый → как есть ═══
    r = _format_addressee("ИП Иванов И.И.")
    check(r == "ИП Иванов И.И.", "ИП → как есть", r)

    r = _format_addressee("ИП. Петров Пётр")
    check(r.startswith("ИП"), "ИП. → как есть", r)

    r = _format_addressee("Самозанятый Сидоров А.А.")
    check("Самозанятый" in r, "Самозанятый → как есть", r)

    # ═══ 3. Marketplace → «Владельцу агрегатора ...» ═══
    r = _format_addressee("Ozon")
    check("Владельцу агрегатора" in r, "Ozon → владелец агрегатора", r)
    check("Интернет Решения" in r, "Ozon → ООО «Интернет Решения»", r)
    check("Ozon" in r, "Ozon: бренд в скобках", r)

    r = _format_addressee("Wildberries")
    check("РВБ" in r, "WB → ООО «РВБ»", r)

    r = _format_addressee("Lamoda")
    check("Купишуз" in r, "Lamoda → ООО «Купишуз»", r)

    r = _format_addressee("Яндекс Маркет")
    check("Владельцу агрегатора" in r and "Яндекс Маркет" in r,
          "Яндекс Маркет → владелец агрегатора", r)

    # ═══ 4. ФИО физлица (3 слова) → «Гражданину/Гражданке» ═══
    r = _format_addressee("Иванов Иван Иванович")
    check("Гражданину" in r, "мужчина → Гражданину", r)
    check("Иванову" in r, "мужчина: фамилия в дательном", r)

    r = _format_addressee("Петрова Мария Ивановна")
    check("Гражданке" in r, "женщина → Гражданке", r)
    check("Петровой" in r, "женщина: фамилия в дательном", r)

    # ═══ 5. 2 слова: Ф И или И Ф ═══
    r = _format_addressee("Иванов Иван")
    check("Гражданину" in r or "Продавцу" in r,
          "2 слова Ф И → Гражданину (или fallback)", r)

    # ═══ 6. 1 слово = имя ═══
    r = _format_addressee("Мария")
    check("Гражданке" in r or "Продавцу" in r,
          "1 слово имя → Гражданке (или fallback)", r)

    # ═══ 7. Ники → «Продавцу X» ═══
    r = _format_addressee("@seller_123")
    check("Продавцу" in r, "ник @... → Продавцу", r)

    r = _format_addressee("ipupkin_1990")
    check("Продавцу" in r, "ник с подчёркиванием → Продавцу", r)

    # ═══ 8. Пустое ═══
    r = _format_addressee("")
    check(r == "Директору", "пусто → Директору (fallback)", r)

    r = _format_addressee(None)
    check(r == "Директору", "None → Директору (fallback)", r)

    # ═══ 9. Мусор (4+ слова не ФИО) ═══
    r = _format_addressee("какой-то странный продавец без имени")
    check("Продавцу" in r, "мусор из 4+ слов → Продавцу", r)

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()