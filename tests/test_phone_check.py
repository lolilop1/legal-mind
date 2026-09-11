"""Offline tests for phone validation. No API calls."""

import _bootstrap  # noqa: F401

from core.phone_check import validate_phone


CASES = [
    ("+7 (999) 123-45-67", True),
    ("8 999 123 45 67", True),
    ("+7 495 123 45 67", True),
    ("9991234567", True),
    ("+7-999-123-45-67", True),
    ("+7 (812) 555-01-01", True),
    ("77777777777777777", False),
    ("7777777777", False),
    ("0000000000", False),
    ("1111111111", False),
    ("1234567890", False),
    ("0123456789", False),
    ("9876543210", False),
    ("", False),
    ("123", False),
    ("12345", False),
    ("12345678901234567890", False),
    ("   ", False),
]


def main():
    passed = 0
    failed = 0
    for source, expected_ok in CASES:
        ok, msg = validate_phone(source)
        if ok == expected_ok:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
            failed += 1
        print(f"[{status}] {source!r:30} -> ok={ok}  {msg[:60]}")

    print(f"\nTotal: {len(CASES)}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()