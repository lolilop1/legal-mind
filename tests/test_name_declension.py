"""Offline tests for the ФИО declension helper. No API calls."""

import _bootstrap  # noqa: F401

from core.name_declension import decline_fio


CASES = [
    ("Иванов Иван Иванович", "Иванова Ивана Ивановича"),
    ("Петров Пётр Петрович", "Петрова Петра Петровича"),
    ("Смирнова Анна Сергеевна", "Смирновой Анны Сергеевны"),
    ("Кузнецова Мария Ивановна", "Кузнецовой Марии Ивановны"),
    ("Сидоров Алексей Дмитриевич", "Сидорова Алексея Дмитриевича"),
    ("", ""),
    ("   ", ""),
    ("Иванов", "Иванов"),
    ("Иванов Иван", "Иванов Иван"),
    ("Ivanov Ivan Ivanovich", "Ivanov Ivan Ivanovich"),
    ("Иванов Иван Иванович Петрович", "Иванов Иван Иванович Петрович"),
]


def main():
    passed = 0
    failed = 0
    for source, expected in CASES:
        try:
            got = decline_fio(source)
        except Exception as e:
            print(f"[FAIL] {source!r}: exception {type(e).__name__}: {e}")
            failed += 1
            continue

        if got == expected:
            print(f"[PASS] {source!r} -> {got!r}")
            passed += 1
        else:
            print(f"[FAIL] {source!r}")
            print(f"       expected: {expected!r}")
            print(f"       got:      {got!r}")
            failed += 1

    print(f"\nTotal: {len(CASES)}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()