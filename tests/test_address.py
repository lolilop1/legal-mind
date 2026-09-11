"""Тесты нормализации адреса."""

import _bootstrap  # noqa: F401

from core.address import format_address


CASES = [
    ("г. Москва ул. Ленина д1", "г. Москва, ул. Ленина, д. 1"),
    ("г. Москва, ул. Ленина, д. 15, кв. 42", "г. Москва, ул. Ленина, д. 15, кв. 42"),
    ("г. Санкт-Петербург, Невский пр., 88", "г. Санкт-Петербург, Невский пр., 88"),
    ("г. Казань ул. Баумана д8 кв15", "г. Казань, ул. Баумана, д. 8, кв. 15"),
    ("Москва ул Ленина 15", "Москва ул Ленина 15"),
    ("", ""),
    ("г. Москва", "г. Москва"),
]


def main():
    passed = 0
    failed = 0
    for src, expected in CASES:
        got = format_address(src)
        ok = got == expected
        if ok:
            passed += 1
            print(f"[PASS] {src!r}")
        else:
            failed += 1
            print(f"[FAIL] {src!r}")
            print(f"       expected: {expected!r}")
            print(f"       got:      {got!r}")

    print(f"\nTotal: {len(CASES)}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()