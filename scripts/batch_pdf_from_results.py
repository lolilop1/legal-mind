"""Batch-generate PDFs from the last results_module2.json run."""

import _bootstrap  # noqa: F401

import json
from pathlib import Path

from modules.uk.pdf import generate_pdf


PLACEHOLDER_REQUISITES = {
    "ук_название": "ООО «УК Тестовая»",
    "фио": "Иванов Иван Иванович",
    "адрес": "г. Тестоград, ул. Тестовая, д. 1, кв. 1",
    "телефон": "+7 (000) 000-00-00",
}


def main():
    _root = Path(__file__).resolve().parent.parent

    src = _root / "results_module2.json"
    if not src.exists():
        print(f"Не найден {src}. Сначала запусти legal_mind_module2_test_v2.py")
        raise SystemExit(1)

    with open(src, "r", encoding="utf-8") as f:
        results = json.load(f)

    outdir = _root / "batch_pdf_output"
    outdir.mkdir(exist_ok=True)

    generated = 0
    skipped = 0

    for i, entry in enumerate(results, start=1):
        name = entry.get("кейс", f"case_{i}")
        out = entry.get("выход", {})

        if out.get("stop"):
            print(f"[SKIP] {name} — stop")
            skipped += 1
            continue

        if out.get("error"):
            print(f"[SKIP] {name} — error: {out['error']}")
            skipped += 1
            continue

        normalized = {
            "описание_проблемы_формальное": out.get("описание_проблемы_формальное", ""),
            "упоминание_повторного_обращения": out.get("упоминание_повторного_обращения", ""),
            "применимые_нормы": out.get("применимые_нормы") or [
                "Статья 161 Жилищного кодекса РФ",
                "Постановление Правительства РФ от 13.08.2006 № 491",
                "Постановление Госстроя РФ от 27.09.2003 № 170",
            ],
        }

        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
        out_path = str(outdir / f"{i:02d}_{safe_name}.pdf")

        try:
            generate_pdf(out_path, PLACEHOLDER_REQUISITES, normalized)
            print(f"[OK]   {name} -> {out_path}")
            generated += 1
        except Exception as e:
            print(f"[FAIL] {name}: {type(e).__name__}: {e}")

    print(f"\nСгенерировано: {generated}  Пропущено (stop/error): {skipped}")
    print(f"PDF-файлы: {outdir.absolute()}")


if __name__ == "__main__":
    main()