# -*- coding: utf-8 -*-
"""Тесты авто-детекта типа документа УК."""

import _bootstrap  # noqa: F401

from modules.uk.doc_detect import detect_doc_type


CASES = [
    # (текст, ожидаемый код)
    ("холодные батареи, дома 15 градусов", "holodnye_batarei"),
    ("сосульки с крыши падают, опасно", "sulki"),
    ("не работает лифт 2 дня", "lift_ostanovka"),
    ("лифт застрял с людьми", "lift_ostanovka"),
    ("залил сосед сверху", "sosed_zatopil"),
    ("сосед сверху залил квартиру", "sosed_zatopil"),
    ("течёт крыша, заливает", "krysha_protechka"),
    ("протечка кровли", "krysha_protechka"),
    ("тараканы в подъезде", "dezinsection"),
    ("крысы в подвале", "deratizaciya"),
    ("перерасчёт за отопление", "pereraschet"),
    ("неверно начислена квитанция", "kvitancia"),
    ("пеня за ЖКУ, списать", "snyatie_peni"),
    ("рассрочка по долгу за ЖКУ", "restrukturizaciya"),
    ("не убирают подъезд две недели", "uborka_podezda"),
    ("снег не убирают во дворе", "sneg_utrambovka"),
    ("гололёд, невозможно ходить", "gololed"),
    ("открытый люк во дворе", "lyuk_yama"),
    ("шлагбаум установить", "shlagbaum"),
    ("кондиционер повесить на фасад", "kondicioner"),
    ("детская площадка сломана", "detskaya_ploshadka"),
    ("качели сломаны, опасно", "kacheli"),
    ("мусоропровод забит, вонь", "musoroprovod"),
    ("переполнена контейнерная площадка", "musor_konteyner"),
    ("ТСЖ не отчитывается", "tszh"),
    ("сменить управляющую компанию", "smena_uk"),
    ("расторгнуть договор с УК", "rastorzhenie"),
    ("общее собрание собственников", "obshchee_sobranie"),
    ("созвать собрание", "obshchee_sobranie"),
    ("запрос информации в УК", "zapros_info"),
    ("копия договора управления", "copy_dogovora"),
    ("иск о защите прав потребителя", "isk_zozpp"),
    ("возражение на судебный приказ", "vozrazhenie_prikaz"),
    ("моральный вред от УК", "moralny_vred"),
    ("обжаловать решение ГЖИ", "obzhalovanie_gzhi"),
    ("жалоба в Роспотребнадзор", "rpn"),
    ("жалоба в прокуратуру", "prokuratura"),
    ("обращение в МЧС", "mchs"),
    ("аварийный дом, признать", "avariynyi_dom"),
    ("перевести в нежилое", "perevod_nezhiloe"),
    ("энергоаудит дома", "energoaudit"),
    ("прямые договоры с РСО", "pryamye_dogovory"),
    # None — не распознано
    ("что-то не так с домом", None),
    ("плохо всё", None),
    ("", None),
]


def main():
    passed = 0
    failed = 0
    for text, expected in CASES:
        got = detect_doc_type(text)
        ok = got == expected
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        marker = "" if ok else f"  (ожидалось {expected})"
        print(f"[{status}] {text[:50]:52} -> {got}{marker}")

    print(f"\nTotal: {len(CASES)}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
