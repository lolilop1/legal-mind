"""Тесты для core.case_id."""

import _bootstrap  # noqa: F401

from datetime import date

from core.case_id import (
    generate_case_uuid,
    format_case_number,
    parse_case_number,
    is_valid_uuid,
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

    u1 = generate_case_uuid()
    u2 = generate_case_uuid()
    check(len(u1) == 32, "UUID: длина 32")
    check(u1 != u2, "UUID: два вызова разные")
    check(all(c in "0123456789abcdef" for c in u1), "UUID: только hex")
    check(is_valid_uuid(u1), "UUID: валидный")
    check(not is_valid_uuid(""), "UUID: пустой невалидный")
    check(not is_valid_uuid("xyz"), "UUID: короткий невалидный")
    check(not is_valid_uuid("z" * 32), "UUID: не-hex невалидный")

    n = format_case_number(date(2026, 9, 11), 1)
    check(n == "LM-20260911-0001", f"Номер: {n}")
    check(format_case_number(date(2026, 9, 11), 4821) == "LM-20260911-4821",
          "Номер: 4-значный seq")
    check(format_case_number(date(2026, 12, 31), 9999) == "LM-20261231-9999",
          "Номер: максимальный seq")

    try:
        format_case_number(date(2026, 9, 11), 10000)
        check(False, "Номер: seq > 9999 должен падать")
    except ValueError:
        check(True, "Номер: seq > 9999 падает")

    try:
        format_case_number(date(2026, 9, 11), 0)
        check(False, "Номер: seq = 0 должен падать")
    except ValueError:
        check(True, "Номер: seq = 0 падает")

    parsed = parse_case_number("LM-20260911-4821")
    check(parsed == (date(2026, 9, 11), 4821), "Парсинг: OK")
    check(parse_case_number("XX-20260911-4821") is None, "Парсинг: неверный префикс")
    check(parse_case_number("LM-20260911-48") is None, "Парсинг: короткий seq")
    check(parse_case_number("LM-20261311-0001") is None, "Парсинг: месяц 13")
    check(parse_case_number("") is None, "Парсинг: пустой")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()