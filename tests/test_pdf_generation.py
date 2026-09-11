"""Offline test for Module 2 PDF generation. No API calls."""

import _bootstrap  # noqa: F401

from pathlib import Path

from modules.uk.pdf import generate_pdf


SAMPLE_REQUISITES = {
    "ук_название": "ООО «УК Жилищник-1»",
    "фио": "Иванов Иван Иванович",
    "адрес": "г. Самара, ул. Ленина, д. 15, кв. 42",
    "телефон": "+7 (999) 123-45-67",
}


NORMS = [
    "Статья 161 Жилищного кодекса РФ",
    "Постановление Правительства РФ от 13.08.2006 № 491",
    "Постановление Госстроя РФ от 27.09.2003 № 170",
]


SAMPLE_CLEAN = {
    "описание_проблемы_формальное": (
        "Управляющей компанией не обеспечивается надлежащая уборка мест "
        "общего пользования в подъезде: в углах скапливается мусор, "
        "наблюдается грязь. Нарушение фиксируется на протяжении примерно "
        "двух недель."
    ),
    "упоминание_повторного_обращения": "",
    "применимые_нормы": NORMS,
}


SAMPLE_WITH_REPEAT = {
    "описание_проблемы_формальное": (
        "В течение месяца наблюдается неисправность домофона, из-за чего "
        "дверь подъезда не закрывается. В подъезд могут беспрепятственно "
        "входить посторонние лица."
    ),
    "упоминание_повторного_обращения": (
        "Ранее обращался(-ась) 01.08.2026, был получен ответ, что проблема "
        "решается, однако ситуация не изменилась."
    ),
    "применимые_нормы": NORMS,
}


SAMPLE_ROOF = {
    "описание_проблемы_формальное": (
        "После дождя с потолка на верхнем этаже течёт вода, на потолке "
        "наблюдаются разводы. Нарушение фиксируется примерно 3 дня, "
        "после последнего сильного дождя."
    ),
    "упоминание_повторного_обращения": "",
    "применимые_нормы": NORMS,
}


def _check_pdf(path: str) -> tuple[bool, str]:
    p = Path(path)
    if not p.exists():
        return False, f"файл не создан: {path}"
    size = p.stat().st_size
    if size < 1000:
        return False, f"файл слишком мал ({size} байт) — вероятно, пустой"
    with open(path, "rb") as f:
        head = f.read(5)
    if head != b"%PDF-":
        return False, f"не похоже на PDF (заголовок: {head!r})"
    return True, f"OK, {size} байт"


def main():
    outdir = Path("test_pdf_output")
    outdir.mkdir(exist_ok=True)

    tests = [
        ("01_clean_cleaning.pdf", SAMPLE_REQUISITES, SAMPLE_CLEAN, "clean cleaning case"),
        ("02_with_repeat.pdf", SAMPLE_REQUISITES, SAMPLE_WITH_REPEAT, "with prior appeal"),
        ("03_roof_leak.pdf", SAMPLE_REQUISITES, SAMPLE_ROOF, "roof leak"),
    ]

    passed = 0
    failed = 0

    for filename, req, norm, label in tests:
        out_path = str(outdir / filename)
        try:
            generate_pdf(out_path, req, norm)
        except Exception as e:
            print(f"[FAIL] {label}: {type(e).__name__}: {e}")
            failed += 1
            continue

        ok, msg = _check_pdf(out_path)
        if ok:
            print(f"[PASS] {label}: {msg}")
            passed += 1
        else:
            print(f"[FAIL] {label}: {msg}")
            failed += 1

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    print(f"PDF-файлы: {outdir.absolute()}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()