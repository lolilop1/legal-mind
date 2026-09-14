# -*- coding: utf-8 -*-
"""Тесты справочника требований."""

import _bootstrap  # noqa: F401

from modules.consumer.demands import (
    DEMANDS, get_demand, list_for_scenario, all_codes,
)


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

    # ─── Справочник ───
    check(len(DEMANDS) >= 8, f"demands: минимум 8 кодов (got {len(DEMANDS)})")

    for code, d in DEMANDS.items():
        check(bool(d.get("label")), f"{code}: label непустой")
        check(bool(d.get("wording")), f"{code}: wording непустой")
        check(isinstance(d.get("deadline_days"), int),
              f"{code}: deadline_days — int")
        check(bool(d.get("deadline_legal")), f"{code}: deadline_legal непустой")
        check(bool(d.get("applicable")), f"{code}: applicable непустой")

    # ─── get_demand ───
    money = get_demand("money")
    check(money is not None, "get: money есть")
    check(money["deadline_days"] == 10, "money: 10 дней")
    check("22" in money["deadline_legal"], "money: ст. 22")
    check(money["code"] == "money", "money: code в ответе")

    repair = get_demand("repair")
    check(repair["deadline_days"] == 45, "repair: 45 дней")
    check("20" in repair["deadline_legal"], "repair: ст. 20")

    replace = get_demand("replace")
    check(replace["deadline_days"] == 7, "replace: 7 дней")
    check("21" in replace["deadline_legal"], "replace: ст. 21")

    check(get_demand("unknown") is None, "get: unknown -> None")
    check(get_demand("") is None, "get: пусто -> None")
    check(get_demand(None) is None, "get: None -> None")

    # ─── list_for_scenario ───
    d_defect = list_for_scenario("defect")
    codes_defect = [d["code"] for d in d_defect]
    check("money" in codes_defect, "defect: money есть")
    check("replace" in codes_defect, "defect: replace есть")
    check("repair" in codes_defect, "defect: repair есть")
    check("exchange" not in codes_defect, "defect: exchange НЕТ (только return14)")

    d_return14 = list_for_scenario("return14")
    codes_r = [d["code"] for d in d_return14]
    check("exchange" in codes_r, "return14: exchange есть")
    check("replace" not in codes_r, "return14: replace НЕТ")

    d_service = list_for_scenario("service")
    codes_s = [d["code"] for d in d_service]
    check("refuse" in codes_s, "service: refuse есть")
    check("fix_free" in codes_s, "service: fix_free есть")
    check("replace" not in codes_s, "service: replace НЕТ")

    d_mp = list_for_scenario("marketplace")
    codes_mp = [d["code"] for d in d_mp]
    check("delivery_refund" in codes_mp, "marketplace: delivery_refund есть")

    check(list_for_scenario("") == [], "пустой сценарий -> []")
    check(list_for_scenario("unknown") == [], "unknown сценарий -> []")

    # ─── all_codes ───
    codes = all_codes()
    check(len(codes) == len(DEMANDS), "all_codes: столько же, сколько DEMANDS")
    check("money" in codes, "all_codes: money есть")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
