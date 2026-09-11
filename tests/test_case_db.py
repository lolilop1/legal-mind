"""Тесты для core.case_db. Используют временную БД."""

import _bootstrap  # noqa: F401

import os
import tempfile
from pathlib import Path


# Переопределяем путь к БД ДО импорта case_db
_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["CASE_DB_PATH"] = _TMP_DB

from core import case_db  # noqa: E402


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

    try:
        # Сбрасываем кэш соединения и путь на всякий случай
        case_db._conn = None
        case_db.DB_PATH = _TMP_DB

        case_db.init_db()
        check(Path(_TMP_DB).exists(), "init_db: файл создан")

        result = case_db.create_case(
            problem_type="uk",
            source_text="в подъезде не убирают",
            user_data={"адрес": "г. Москва, ул. Ленина, 15"},
            dna={
                "subject": "жилец",
                "object": "подъезд",
                "event": "не убирают",
                "jurisdiction": "Москва",
            },
            engine_version="uk-01",
            rules_version="2026.09",
            template_version="1.0",
        )
        check("case_number" in result, "create: есть номер")
        check("case_uuid" in result, "create: есть UUID")
        check(result["case_number"].startswith("LM-"), "create: формат номера")

        num = result["case_number"]
        uid = result["case_uuid"]

        case = case_db.get_case(num, uid)
        check(case is not None, "get: найден")
        check(case["problem_type"] == "uk", "get: тип")
        check(case["jurisdiction"] == "Москва", "get: регион")
        check(case["engine_version"] == "uk-01", "get: engine_version")

        check(case_db.get_case(num, "0" * 32) is None, "get: неверный UUID → None")
        check(case_db.get_case(num, "abc") is None, "get: короткий UUID → None")
        check(case_db.get_case("XXX", uid) is None, "get: неверный номер → None")

        ok = case_db.update_case(num, uid, {"amount": 15000, "demand": "вернуть деньги"})
        check(ok, "update: OK")
        case = case_db.get_case(num, uid)
        check(case["amount"] == 15000, "update: amount")
        check(case["demand"] == "вернуть деньги", "update: demand")

        doc_id = case_db.add_document(num, "claim", b"PDF_CONTENT", template_version="1.0")
        check(doc_id > 0, "add_document: id")
        docs = case_db.get_documents(num)
        check(len(docs) == 1, "add_document: список")
        check(docs[0]["doc_type"] == "claim", "add_document: тип")

        content = case_db.get_document_content(doc_id)
        check(content == b"PDF_CONTENT", "add_document: содержимое")

        events = case_db.get_events(num)
        check(len(events) >= 3, f"events: >= 3 (получено {len(events)})")

        result2 = case_db.create_case("noise", "шум", {"адрес": "X"}, dna={})
        check(result2["case_number"] != num, "второй CASE: другой номер")

        st = case_db.stats()
        check(st["total"] == 2, f"stats: total 2 (получено {st['total']})")

        check(case_db.delete_case(num, uid), "delete: OK")
        check(case_db.get_case(num, uid) is None, "delete: после удаления None")

    finally:
        try:
            os.unlink(_TMP_DB)
        except OSError:
            pass

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()