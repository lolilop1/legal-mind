"""Тесты справочника маркетплейсов."""

import _bootstrap  # noqa: F401

from modules.consumer.marketplaces import (
    MARKETPLACES,
    resolve_marketplace,
    is_marketplace,
    all_aliases,
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
    check(len(MARKETPLACES) == 12, f"12 площадок в справочнике (получено {len(MARKETPLACES)})")

    for key, data in MARKETPLACES.items():
        check(bool(data.get("brand")), f"{key}: brand непустой")
        check(bool(data.get("entity")), f"{key}: entity непустой")
        check(bool(data.get("aliases")), f"{key}: aliases непустой")

    # ─── resolve_marketplace ───
    check(resolve_marketplace("Ozon") is not None, "resolve: Ozon")
    check(resolve_marketplace("озон") is not None, "resolve: озон (строчная)")
    check(resolve_marketplace("OZON") is not None, "resolve: OZON (caps)")
    check(resolve_marketplace("Lamoda") is not None, "resolve: Lamoda")
    check(resolve_marketplace("ламода") is not None, "resolve: ламода")
    check(resolve_marketplace("Яндекс Маркет") is not None, "resolve: Яндекс Маркет")
    check(resolve_marketplace("WB") is not None, "resolve: WB")
    check(resolve_marketplace("Магнит Маркет") is not None, "resolve: Магнит Маркет")
    check(resolve_marketplace("Купер") is not None, "resolve: Купер")
    check(resolve_marketplace("СберМаркет") is not None, "resolve: СберМаркет (алиас Купера)")
    check(resolve_marketplace("Joom") is not None, "resolve: Joom")

    # ─── Реквизиты Ozon ───
    ozon = resolve_marketplace("Ozon")
    check(ozon is not None and "Интернет Решения" in ozon["entity"],
          "Ozon: entity = ООО «Интернет Решения»")
    check(ozon is not None and ozon["inn"] == "7704217370",
          "Ozon: ИНН 7704217370")

    # ─── Lamoda ───
    lamoda = resolve_marketplace("Lamoda")
    check(lamoda is not None and "Купишуз" in lamoda["entity"],
          "Lamoda: entity = ООО «Купишуз»")

    # ─── WB (новые реквизиты РВБ) ───
    wb = resolve_marketplace("Wildberries")
    check(wb is not None and "РВБ" in wb["entity"],
          "WB: entity = ООО «РВБ»")

    # ─── Отрицательные ───
    check(resolve_marketplace("Мария Петрова") is None, "resolve: физлицо → None")
    check(resolve_marketplace("ООО Ромашка") is None, "resolve: обычное ООО → None")
    check(resolve_marketplace("") is None, "resolve: пусто → None")
    check(resolve_marketplace(None) is None, "resolve: None → None")

    # ─── is_marketplace ───
    check(is_marketplace("Ozon") is True, "is_marketplace: Ozon True")
    check(is_marketplace("Мария Петрова") is False, "is_marketplace: физлицо False")

    # ─── all_aliases ───
    aliases = all_aliases()
    check(len(aliases) >= 30, f"all_aliases: >=30 (получено {len(aliases)})")
    check("ozon" in aliases, "all_aliases: ozon есть")

    # ─── Уникальность алиасов ───
    seen = {}
    dupes = []
    for key, data in MARKETPLACES.items():
        for alias in data["aliases"]:
            if alias in seen:
                dupes.append(f"{alias} ({seen[alias]} vs {key})")
            seen[alias] = key
    check(not dupes, f"алиасы уникальны (дубли: {dupes})")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
