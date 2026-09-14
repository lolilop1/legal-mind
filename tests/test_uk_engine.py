# -*- coding: utf-8 -*-
"""Тесты modules/uk/engine.py. LLM замокан."""

import _bootstrap  # noqa: F401

from pathlib import Path
from unittest.mock import patch

import modules.uk.engine as uk_engine


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

    def _fake_ok(inst, usr):
        return {"parsed": {
            "описание_проблемы_формальное": "В подъезде не производится уборка мест общего пользования.",
            "упоминание_повторного_обращения": "",
            "применимые_нормы": [
                "Статья 161 Жилищного кодекса РФ",
                "Постановление Правительства РФ от 13.08.2006 № 491",
                "Постановление Госстроя РФ от 27.09.2003 № 170",
            ],
        }}

    user_data = {
        "проблема": "в подъезде не убирают уже две недели, грязь и мусор",
        "адрес": "г. Москва, ул. Ленина, д. 15",
        "дата_начала": "две недели",
    }

    # 1. uk OK
    with patch.object(uk_engine, "_call_llm", _fake_ok):
        r = uk_engine.process_uk(user_data, "uk")
    check(r["kind"] == "ok", "uk: kind=ok")
    check(len(r["parsed"]["применимые_нормы"]) == 3, "uk: 3 нормы")
    check(r["doc_type"] == "uk", "uk: doc_type=uk")

    # 2. неизвестный doc_type
    r = uk_engine.process_uk(user_data, "unknown_xyz")
    check(r["kind"] == "error", "unknown doc_type: error")

    # 3. конфиг gzhi загружается
    from modules.uk.configs.gzhi import CONFIG as G
    check(G["code"] == "gzhi", "gzhi config: code=gzhi")
    check("7.22" in " ".join(G["allowed_norms"]), "gzhi: 7.22 КоАП в нормах")

    # 4. конфиг prokuratura
    from modules.uk.configs.prokuratura import CONFIG as P
    check(P["code"] == "prokuratura", "prokuratura: code")

    # 5. конфиг damage
    from modules.uk.configs.damage import CONFIG as D
    check(D["code"] == "damage", "damage: code")
    check("1064" in " ".join(D["allowed_norms"]), "damage: 1064 ГК")

    # 5b. all 16 configs загружаются
    import os
    _CONFIGS_DIR = Path(__file__).resolve().parent.parent / "modules" / "uk" / "configs"
    codes = sorted([f.stem for f in _CONFIGS_DIR.glob("*.py") if f.name != "__init__.py"])
    for code in codes:
        cfg = uk_engine._get_config(code)
        check(cfg is not None and cfg.get("code") == code,
              f"config {code}: загружается")
        check("allowed_norms" in cfg and len(cfg["allowed_norms"]) >= 2,
              f"config {code}: allowed_norms >= 2")
        check("pdf_title" in cfg, f"config {code}: pdf_title есть")

    # 6. конфиг rpn
    from modules.uk.configs.rpn import CONFIG as R
    check(R["code"] == "rpn", "rpn: code")

    # 7. нормы не из whitelist → error
    def _fake_bad(inst, usr):
        return {"parsed": {
            "описание_проблемы_формальное": "тест",
            "применимые_нормы": ["Статья 999 ФЗ «Несуществующий»"],
        }}
    with patch.object(uk_engine, "_call_llm", _fake_bad):
        r = uk_engine.process_uk(user_data, "uk")
    check(r["kind"] == "error", "whitelist: error на левой норме")

    # 8. пустое описание → error
    def _fake_empty(inst, usr):
        return {"parsed": {
            "описание_проблемы_формальное": "",
            "применимые_нормы": ["Статья 161 Жилищного кодекса РФ"],
        }}
    with patch.object(uk_engine, "_call_llm", _fake_empty):
        r = uk_engine.process_uk(user_data, "uk")
    check(r["kind"] == "error", "пустое описание: error")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
