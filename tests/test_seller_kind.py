"""Тесты seller_kind — единая точка правды для _is_legal_entity."""

import _bootstrap  # noqa: F401

from modules.consumer.seller_kind import (
    is_legal_entity, is_marketplace, LEGAL_PREFIXES,
)


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

    # Юрлица
    for prefix in LEGAL_PREFIXES:
        check(is_legal_entity(f"{prefix} Тест") is True,
              f"{prefix} Тест -> True")
        check(is_legal_entity(f"{prefix}. Тест") is True,
              f"{prefix}. Тест -> True")

    # ИП / самозанятый
    check(is_legal_entity("ИП Иванов И.И.") is True, "ИП -> True")
    check(is_legal_entity("ИП. Иванов") is True, "ИП. -> True")
    check(is_legal_entity("Самозанятый Петров") is True, "Самозанятый -> True")
    check(is_legal_entity("самозанятая Иванова") is True, "самозанятая -> True")

    # Маркетплейсы
    check(is_legal_entity("Ozon") is True, "Ozon -> True")
    check(is_legal_entity("Wildberries") is True, "WB -> True")
    check(is_legal_entity("Ламода") is True, "Ламода -> True")

    # Физлица
    check(is_legal_entity("Мария Петрова") is False, "физлицо -> False")
    check(is_legal_entity("ivan_petrov") is False, "ник -> False")
    check(is_legal_entity("Продавец") is False, "слово -> False")

    # Пустое -> True (консервативно)
    check(is_legal_entity("") is True, "пусто -> True")
    check(is_legal_entity(None) is True, "None -> True")
    check(is_legal_entity("   ") is True, "пробелы -> True")

    # is_marketplace
    check(is_marketplace("Ozon") is True, "is_marketplace: Ozon")
    check(is_marketplace("Мария Петрова") is False, "is_marketplace: физлицо")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()