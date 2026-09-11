"""Тесты для Legal Trace."""

import _bootstrap  # noqa: F401

from core.trace import build_trace


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

    # ─── Модуль 2 (УК) ───
    t1 = build_trace(
        problem_type="uk",
        problem_text="в подъезде не убирают уже две недели",
        norms=["Статья 161 ЖК РФ", "Постановление № 491"],
    )
    check(t1.fact.startswith("в подъезде не убирают"), "UK: факт сохранён")
    check("ненадлежащее содержание" in t1.qualification, "UK: квалификация")
    check(len(t1.norms) == 2, "UK: две нормы")
    check("consultant" in t1.source, "UK: источник")
    check(not t1.is_empty(), "UK: не пустой")

    # ─── Модуль 3 (шум) ───
    t2 = build_trace(
        problem_type="noise",
        problem_text="соседи сверху слушают музыку ночью",
        norms=["Закон г. Москвы от 12.07.2002 № 42"],
        source="https://base.garant.ru/378789/",
    )
    check("соседи сверху" in t2.fact, "Шум: факт")
    check("нарушение тишины" in t2.qualification, "Шум: квалификация")
    check(len(t2.norms) == 1, "Шум: одна норма")
    check("garant.ru" in t2.source, "Шум: источник из аргумента")

    # ─── Обрезка длинного текста ───
    long_text = "а" * 200
    t3 = build_trace("uk", long_text, norms=["X"])
    check(len(t3.fact) <= 120, "Длинный текст обрезан до 120")
    check(t3.fact.endswith("..."), "Многоточие в конце")

    # ─── Пустой текст ───
    t4 = build_trace("uk", "", norms=[])
    check(t4.fact == "", "Пустой факт")
    check(t4.is_empty(), "Пустой trace")

    # ─── Сериализация ───
    d = t1.to_dict()
    check("fact" in d and "qualification" in d, "to_dict: ключи")
    check(isinstance(d["norms"], list), "to_dict: norms — список")

    # ─── Неизвестный модуль ───
    t5 = build_trace("unknown", "test text", norms=["Y"])
    check("юридически значимое" in t5.qualification, "Неизвестный модуль: fallback")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()