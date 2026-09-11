"""Тесты для pre-checks модулей 2 и 3."""

import _bootstrap  # noqa: F401

from modules.uk.pre_checks import run_uk_pre_checks
from modules.noise.pre_checks import run_noise_pre_checks


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
    r1 = run_uk_pre_checks({
        "проблема": "в подъезде не убирают уже две недели, мусор",
        "адрес": "г. Москва, ул. Ленина, 15",
        "дата_начала": "около двух недель",
        "обращались_ранее": "нет",
    })
    check(not r1.is_blocked, "УК: нормальное описание — не блокируется")
    check(any("Объект" in k.label for k in r1.known), "УК: объект определён")
    check(not r1.missing_critical, "УК: нет критичных пропусков")

    r2 = run_uk_pre_checks({
        "проблема": "ну что-то там не так с домом в целом",
        "адрес": "г. Москва",
        "дата_начала": "",
        "обращались_ранее": "нет",
    })
    check(r2.is_blocked, "УК: vague без объекта — блокируется")
    check(len(r2.missing_critical) >= 1, "УК: есть критичное")
    check(len(r2.missing_optional) >= 1, "УК: есть опциональное")

    r3 = run_uk_pre_checks({
        "проблема": "не работает лифт уже неделю",
        "адрес": "г. Москва",
        "дата_начала": "неделю",
        "обращались_ранее": "да, 01.08.2026",
    })
    check(not r3.is_blocked, "УК: лифт — не блокируется")
    check(any("Лифт" in (k.value or "") for k in r3.known),
          "УК: объект — Лифт")

    # ─── Модуль 3 (Шум) ───
    r4 = run_noise_pre_checks({
        "проблема": "соседи сверху слушают музыку ночью, не дают спать",
        "адрес": "г. Москва",
        "дата_начала": "месяц",
    }, extras={"region": "Москва"})
    check(not r4.is_blocked, "Шум: полное описание — не блокируется")
    check(any("Музыка" in (k.value or "") for k in r4.known),
          "Шум: вид — Музыка")
    check(any("сверху" in (k.value or "").lower() for k in r4.known),
          "Шум: источник — сверху")
    check(any("Ночн" in (k.value or "") for k in r4.known),
          "Шум: время — ночь")

    r5 = run_noise_pre_checks({
        "проблема": "какой-то шум постоянно, не могу жить",
        "адрес": "г. Москва",
        "дата_начала": "",
    }, extras={})
    check(r5.is_blocked, "Шум: без вида и источника — блокируется")
    check(len(r5.missing_critical) == 2, "Шум: два критичных")

    r6 = run_noise_pre_checks({
        "проблема": "сосед сверху лает как собака, я не знаю что делать",
        "адрес": "г. Москва",
        "дата_начала": "",
    }, extras={"region": "Москва"})
    # «собак» в «собака» — матчит первое правило _NOISE_TYPE
    # «лает» → Лай собаки — тоже ловит
    check(any("Лай" in (k.value or "") for k in r6.known),
          "Шум: лай собаки определён")

    r7 = run_noise_pre_checks({
        "проблема": "из квартиры №45 громкая музыка по ночам",
        "адрес": "г. Москва",
        "дата_начала": "",
    }, extras={})
    check(any("Конкретн" in (k.value or "") for k in r7.known),
          "Шум: источник — конкретная квартира")
    check(any("Регион" in k.label for k in r7.missing_optional),
          "Шум: регион в опциональных")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()