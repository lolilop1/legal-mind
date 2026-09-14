# -*- coding: utf-8 -*-
"""Тесты engine.py: anchor-norms fallback. LLM замокан."""

import _bootstrap  # noqa: F401

import sys
from unittest.mock import patch


import modules.consumer.engine as engine


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

    ZPP = "Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»"
    ART_18 = f"Статья 18 {ZPP}"
    ART_22 = f"Статья 22 {ZPP}"

    def _fake_llm_no_anchor(inst, usr):
        # Ответ без якорной нормы (только ст. 22, которая не якорная для defect)
        return {"parsed": {
            "описание_проблемы_формальное": "тестовое описание",
            "требование": "вернуть деньги",
            "применимые_нормы": [ART_22],
        }}

    def _fake_llm_with_anchor(inst, usr):
        return {"parsed": {
            "описание_проблемы_формальное": "тестовое описание",
            "требование": "вернуть деньги",
            "применимые_нормы": [ART_18, ART_22],
        }}

    def _fake_llm_bad_norm(inst, usr):
        # Не из whitelist
        return {"parsed": {
            "описание_проблемы_формальное": "тестовое",
            "требование": "вернуть",
            "применимые_нормы": ["Статья 999 ФЗ «Несуществующий»"],
        }}

    user_data = {
        "проблема": "купил смартфон, сломался",
        "продавец": "ООО Тест",
        "адрес_продавца": "Москва",
    }

    # ═══ 1. Нормы без якорной → engine добавил ═══
    with patch.object(engine, "_call_llm", _fake_llm_no_anchor):
        r = engine.process_consumer(user_data, "defect")
    check(r["kind"] == "ok", "anchor-fallback: kind=ok")
    norms = r["parsed"]["применимые_нормы"]
    check(ART_18 in norms, f"anchor-fallback: ст. 18 добавлена (norms={norms})")
    check(r["parsed"].get("_anchor_fallback") is True, "anchor-fallback: флаг выставлен")
    check(norms[0] == ART_18, "anchor-fallback: якорная — первая в списке")

    # ═══ 2. Нормы с якорной → fallback не сработал ═══
    with patch.object(engine, "_call_llm", _fake_llm_with_anchor):
        r = engine.process_consumer(user_data, "defect")
    check(r["kind"] == "ok", "anchor-ok: kind=ok")
    check(r["parsed"].get("_anchor_fallback") is None, "anchor-ok: флаг НЕ выставлен")
    check(ART_18 in r["parsed"]["применимые_нормы"], "anchor-ok: ст. 18 на месте")

    # ═══ 3. Норма не из whitelist → error ═══
    with patch.object(engine, "_call_llm", _fake_llm_bad_norm):
        r = engine.process_consumer(user_data, "defect")
    check(r["kind"] == "error", "whitelist: kind=error")
    check("недопустимые" in r["message"].lower(), "whitelist: правильное сообщение")

    # ═══ 4. Неизвестный сценарий → error ═══
    r = engine.process_consumer(user_data, "unknown_scenario")
    check(r["kind"] == "error", "unknown scenario: kind=error")

    # ═══ 5. У return14 anchor_norms = [ст. 25] ═══
    from modules.consumer.configs.return14 import CONFIG as RET14
    check(len(RET14.get("anchor_norms", [])) == 1,
          f"return14: 1 anchor (got {len(RET14.get('anchor_norms', []))})")

    # ═══ 6. У service anchor_norms = 5 ═══
    from modules.consumer.configs.service import CONFIG as SVC
    check(len(SVC.get("anchor_norms", [])) == 5,
          f"service: 5 anchors (got {len(SVC.get('anchor_norms', []))})")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()