"""Offline tests for phone validation and normalization. No API calls."""

import _bootstrap  # noqa: F401

from core.phone_check import validate_phone, normalize_phone


VALID_CASES = [
    ("+7 (999) 123-45-67", True),
    ("8 999 123 45 67", True),
    ("+7 495 123 45 67", True),
    ("9991234567", True),
    ("+7-999-123-45-67", True),
    ("+7 (812) 555-01-01", True),
]

INVALID_CASES = [
    ("77777777777777777", "длинн"),
    ("7777777777", "одинаков"),
    ("0000000000", "одинаков"),
    ("1111111111", "одинаков"),
    ("1234567890", "по порядку"),
    ("0123456789", "по порядку"),
    ("9876543210", "по порядку"),
    ("", "не примут"),
    ("123", "коротк"),
    ("12345", "коротк"),
    ("12345678901234567890", "длинн"),
    ("   ", "не примут"),
    # Усиленная проверка РФ: 12+ цифр с началом 7/8
    ("+7 999 123 45 67 89", "лишние цифры"),
    ("8 999 123 45 67 8", "лишние цифры"),
]

NORMALIZE_CASES = [
    ("+7 (999) 123-45-67", "+7 (999) 123-45-67"),
    ("8 999 123 45 67", "+7 (999) 123-45-67"),
    ("9991234567", "+7 (999) 123-45-67"),
    ("+7-999-123-45-67", "+7 (999) 123-45-67"),
    ("+79879089086", "+7 (987) 908-90-86"),
    ("89879089086", "+7 (987) 908-90-86"),
    ("9879089086", "+7 (987) 908-90-86"),
    ("+49 30 123456", "+4930123456"),
    ("", ""),
    ("abc", ""),
]


def main():
    passed = 0
    failed = 0

    print("=== Валидация (должны проходить) ===")
    for source, expected_ok in VALID_CASES:
        ok, msg = validate_phone(source)
        if ok == expected_ok:
            print(f"[PASS] {source!r:30} -> ok")
            passed += 1
        else:
            print(f"[FAIL] {source!r:30} -> ok={ok} (ожидалось {expected_ok})")
            failed += 1

    print()
    print("=== Валидация (должны падать с текстом) ===")
    for source, keyword in INVALID_CASES:
        ok, msg = validate_phone(source)
        if ok is False and keyword in msg.lower():
            print(f"[PASS] {source!r:30} -> fail: {msg[:60]}")
            passed += 1
        else:
            print(f"[FAIL] {source!r:30} -> ok={ok}, msg={msg[:60]!r}")
            failed += 1

    print()
    print("=== Нормализация ===")
    for source, expected in NORMALIZE_CASES:
        got = normalize_phone(source)
        if got == expected:
            print(f"[PASS] {source!r:25} -> {got!r}")
            passed += 1
        else:
            print(f"[FAIL] {source!r:25}")
            print(f"       expected: {expected!r}")
            print(f"       got:      {got!r}")
            failed += 1

    total = len(VALID_CASES) + len(INVALID_CASES) + len(NORMALIZE_CASES)
    print(f"\nTotal: {total}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
