# -*- coding: utf-8 -*-
"""Все 181 конфиг УК загружаются и имеют нужные поля. Без PDF."""

import _bootstrap  # noqa: F401

from pathlib import Path
from modules.uk.engine import _get_config


_CONFIGS_DIR = Path(__file__).resolve().parent.parent / "modules" / "uk" / "configs"
REQUIRED_FIELDS = ("code", "title", "addressee", "article",
                   "pdf_title", "pdf_subtitle", "pdf_request_block",
                   "allowed_norms", "llm_hints")


def main():
    codes = sorted([f.stem for f in _CONFIGS_DIR.glob("*.py")
                    if f.name != "__init__.py"])

    passed = 0
    failed = 0

    def check(cond, label):
        nonlocal passed, failed
        if cond:
            passed += 1
        else:
            print(f"[FAIL] {label}")
            failed += 1

    print(f"Конфигов: {len(codes)}\n")

    for code in codes:
        cfg = _get_config(code)
        if cfg is None:
            check(False, f"{code}: не загрузился")
            continue

        # code совпадает с именем файла
        check(cfg.get("code") == code, f"{code}: code == имени файла")

        # все обязательные поля
        missing = [f for f in REQUIRED_FIELDS if f not in cfg or not cfg[f]]
        check(not missing, f"{code}: нет полей {missing}")

        # нормы: >= 2
        check(len(cfg.get("allowed_norms", [])) >= 2,
              f"{code}: allowed_norms >= 2")

        # llm_hints: >= 2
        check(len(cfg.get("llm_hints", [])) >= 2,
              f"{code}: llm_hints >= 2")

    print(f"Total: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
