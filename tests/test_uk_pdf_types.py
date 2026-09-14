# -*- coding: utf-8 -*-
"""Тесты PDF для 5 типов документов модуля УК."""

import _bootstrap  # noqa: F401

from pathlib import Path
from modules.uk.pdf import generate_pdf


REQ = {
    "ук_название": "ООО «УК Тестовая»",
    "фио": "Иванов Иван Иванович",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "телефон": "+7 (999) 123-45-67",
}

NORM = {
    "описание_проблемы_формальное": "В подъезде не производится уборка мест общего пользования.",
    "упоминание_повторного_обращения": "",
    "применимые_нормы": ["Статья 161 Жилищного кодекса РФ"],
}


def main():
    import tempfile
    import pypdf
    import io

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

    from modules.uk.configs.uk import CONFIG as UK
    from modules.uk.configs.gzhi import CONFIG as GZHI
    from modules.uk.configs.rpn import CONFIG as RPN
    from modules.uk.configs.prokuratura import CONFIG as PROK
    from modules.uk.configs.damage import CONFIG as DMG

    def _pdf_text(cfg):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        generate_pdf(path, REQ, NORM, config=cfg)
        data = Path(path).read_bytes()
        Path(path).unlink()
        reader = pypdf.PdfReader(io.BytesIO(data))
        return "\n".join(p.extract_text() or "" for p in reader.pages)

    # 1. UK — ЗАЯВЛЕНИЕ + ПРОШУ
    t = _pdf_text(UK)
    check("ЗАЯВЛЕНИЕ" in t, "uk: ЗАЯВЛЕНИЕ")
    check("ПРОШУ:" in t, "uk: ПРОШУ:")

    # 2. ГЖИ — ЖАЛОБА
    t = _pdf_text(GZHI)
    check("ЖАЛОБА" in t, "gzhi: ЖАЛОБА")
    check("ПРОШУ:" in t, "gzhi: ПРОШУ:")

    # 3. РПН — ЖАЛОБА
    t = _pdf_text(RPN)
    check("ЖАЛОБА" in t, "rpn: ЖАЛОБА")

    # 4. Прокуратура — ЗАЯВЛЕНИЕ
    t = _pdf_text(PROK)
    check("ЗАЯВЛЕНИЕ" in t, "prokuratura: ЗАЯВЛЕНИЕ")

    # 5. Damage — ПРЕТЕНЗИЯ + ТРЕБУЮ
    t = _pdf_text(DMG)
    check("ПРЕТЕНЗИЯ" in t, "damage: ПРЕТЕНЗИЯ")
    check("ТРЕБУЮ:" in t, "damage: ТРЕБУЮ:")

    # 6. Без config — дефолт (ЗАЯВЛЕНИЕ)
    t = _pdf_text({})
    check("ЗАЯВЛЕНИЕ" in t, "no config: дефолт ЗАЯВЛЕНИЕ")

    # 7. Все 16 конфигов генерируют PDF
    import modules.uk.engine as eng
    codes = ["uk","gzhi","rpn","prokuratura","damage","pereraschet",
             "zapros_info","kvitancia","ads","tszh","kapremont",
             "municipality","act","s_o_s","rastorzhenie","snizhenie"]
    for code in codes:
        cfg = eng._get_config(code)
        try:
            txt = _pdf_text(cfg)
            ok = len(txt) > 200 and cfg["pdf_title"] in txt
            check(ok, f"{code}: PDF валиден ({len(txt)} симв.)")
        except Exception as e:
            check(False, f"{code}: PDF упал — {type(e).__name__}: {e}")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
