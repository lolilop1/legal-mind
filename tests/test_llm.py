# -*- coding: utf-8 -*-
"""Тесты core.llm: обработка ошибок API, парсинг, отсутствие ключей.

Реальный Yandex API НЕ вызывается — openai-клиент замокан.
"""

import _bootstrap  # noqa: F401

import os
import sys
from unittest.mock import MagicMock, patch


# ═══ Готовим env ДО импорта ═══
# ВАЖНО: используем прямое присваивание, НЕ setdefault —
# в CI YANDEX_API_KEY="" (пустой), а setdefault не перезаписывает.
os.environ["YANDEX_API_KEY"] = "test-key"
os.environ["YANDEX_FOLDER_ID"] = "test-folder"

import core.llm as llm

# Страховка: если load_dotenv из web/.env перезаписал наши значения
# (в CI файла нет, локально может быть) — принудительно ставим наши.
llm.API_KEY = "test-key"
llm.FOLDER = "test-folder"

# Отключаем sleep в retry — иначе тесты тормозят на 3+ сек
llm.time.sleep = lambda s: None


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

    # ═══ 1. Нет ключей → {'error': ...} ═══
    with patch.object(llm, "API_KEY", ""), patch.object(llm, "FOLDER", ""):
        r = llm.call_alice_flash("инстр", "ввод")
        check("error" in r, "нет ключей → error в ответе")
        check("YANDEX" in r["error"] or "настроен" in r["error"].lower(),
              "ошибка упоминает YANDEX")

    with patch.object(llm, "API_KEY", "k"), patch.object(llm, "FOLDER", ""):
        r = llm.call_alice_flash("инстр", "ввод")
        check("error" in r, "только API_KEY, без FOLDER → error")

    # ═══ 2. Успешный вызов ═══
    fake_resp = MagicMock()
    fake_resp.output_text = '{"описание_проблемы_формальное": "test"}'
    fake_usage = MagicMock()
    fake_usage.input_tokens = 42
    fake_usage.output_tokens = 17
    fake_resp.usage = fake_usage

    fake_client = MagicMock()
    fake_client.responses.create.return_value = fake_resp

    with patch.object(llm, "_get_client", return_value=fake_client):
        r = llm.call_alice_flash("инстр", "ввод")
        check("error" not in r, "успех: нет error")
        check(r.get("text") == '{"описание_проблемы_формальное": "test"}',
              "успех: текст получен")
        check(r.get("input_tokens") == 42, "успех: input_tokens")
        check(r.get("output_tokens") == 17, "успех: output_tokens")

    # ═══ 3. API бросает исключение ═══
    fake_client_err = MagicMock()
    fake_client_err.responses.create.side_effect = RuntimeError("API down")

    with patch.object(llm, "_get_client", return_value=fake_client_err):
        r = llm.call_alice_flash("инстр", "ввод")
        check("error" in r, "API упал → error в ответе")
        check("RuntimeError" in r["error"], "error упоминает RuntimeError")
        check("API down" in r["error"], "error содержит текст исключения")

    # ═══ 4. Парсинг ошибки (response.output_text недоступен) ═══
    # ВАЖНО: не MagicMock — он через __getattr__ возвращает мок вместо
    # того, чтобы пробросить AttributeError. Нужен обычный класс.
    class _BadResponse:
        def __getattr__(self, name):
            raise AttributeError(f"no {name}")

    fake_client_bad = MagicMock()
    fake_client_bad.responses.create.return_value = _BadResponse()

    with patch.object(llm, "_get_client", return_value=fake_client_bad):
        r = llm.call_alice_flash("инстр", "ввод")
        check("error" in r, "output_text недоступен → error")
        check("parse" in r["error"] or "AttributeError" in r["error"],
              "error в категории parse")

    # ═══ 5. call_alice_pro ═══
    fake_client_pro = MagicMock()
    fake_resp_pro = MagicMock()
    fake_resp_pro.output_text = "pro-ответ"
    fake_resp_pro.usage = None  # проверяем что не падает без usage
    fake_client_pro.responses.create.return_value = fake_resp_pro

    with patch.object(llm, "_get_client", return_value=fake_client_pro):
        r = llm.call_alice_pro("инстр", "ввод")
        check("error" not in r, "call_alice_pro: успех без usage")
        check(r.get("text") == "pro-ответ", "call_alice_pro: текст")
        check("input_tokens" not in r, "call_alice_pro: нет usage → нет токенов")

    # ═══ 6. Модели в URL ═══
    fake_client_url = MagicMock()
    fake_client_url.responses.create.return_value = fake_resp
    with patch.object(llm, "_get_client", return_value=fake_client_url), \
         patch.object(llm, "API_KEY", "k"), \
         patch.object(llm, "FOLDER", "f"):
        llm.call_alice_flash("i", "u")
        args, kwargs = fake_client_url.responses.create.call_args
        model_used = kwargs.get("model", "")
        check("aliceai-llm-flash" in model_used,
              f"flash: modelUri содержит 'aliceai-llm-flash' ({model_used[:80]})")

        fake_client_url.responses.create.reset_mock()
        llm.call_alice_pro("i", "u")
        args, kwargs = fake_client_url.responses.create.call_args
        model_used = kwargs.get("model", "")
        check("aliceai-llm" in model_used and "flash" not in model_used,
              f"pro: modelUri содержит 'aliceai-llm' без flash")

    # ═══ 7. URL — Yandex endpoint ═══
    check(llm.BASE_URL == "https://ai.api.cloud.yandex.net/v1",
          "BASE_URL — Yandex endpoint")

    # ═══ 8. _get_client не падает при валидных env ═══
    with patch.object(llm, "API_KEY", "k"), patch.object(llm, "FOLDER", "f"):
        try:
            c = llm._get_client()
            check(c is not None, "_get_client возвращает клиента")
        except Exception as e:
            check(False, f"_get_client падает: {e}")

    # ═══ 9. Retry: успех после 2 неудач ═══
    _c9 = {"n": 0}
    def _fail_twice(*a, **kw):
        _c9["n"] += 1
        if _c9["n"] < 3:
            raise llm.openai.APITimeoutError(
                request=MagicMock()
            )
        return fake_resp

    fc9 = MagicMock()
    fc9.responses.create.side_effect = _fail_twice
    with patch.object(llm, "_get_client", return_value=fc9):
        r = llm.call_alice_flash("i", "u")
        check("error" not in r, "retry: успех после 2 неудач")
        check(r.get("text") == '{"описание_проблемы_формальное": "test"}',
              "retry: текст получен после retry")
        check(_c9["n"] == 3, f"retry: 3 вызова (получено {_c9['n']})")

    # ═══ 10. Retry: клиентская ошибка НЕ ретраится ═══
    # Подменяем _NO_RETRY_ERRORS — не зависим от httpx/openai версии
    class _FakeAuthError(Exception):
        pass

    _c10 = {"n": 0}
    def _client_error(*a, **kw):
        _c10["n"] += 1
        raise _FakeAuthError("bad key")

    fc10 = MagicMock()
    fc10.responses.create.side_effect = _client_error
    with patch.object(llm, "_NO_RETRY_ERRORS", (_FakeAuthError,)), \
         patch.object(llm, "_get_client", return_value=fc10):
        r = llm.call_alice_flash("i", "u")
        check("error" in r, "retry: клиентская ошибка → error")
        check(_c10["n"] == 1, f"retry: клиентская без повторов (вызовов {_c10['n']})")

    # ═══ 11. Retry: 3 раза падает → error, 3 вызова ═══
    _c11 = {"n": 0}
    def _always_timeout(*a, **kw):
        _c11["n"] += 1
        raise llm.openai.APITimeoutError(
            request=MagicMock()
        )

    fc11 = MagicMock()
    fc11.responses.create.side_effect = _always_timeout
    with patch.object(llm, "_get_client", return_value=fc11):
        r = llm.call_alice_flash("i", "u")
        check("error" in r, "retry: всё упало → error")
        check(_c11["n"] == 3, f"retry: 3 попытки (получено {_c11['n']})")
        check("APITimeoutError" in r["error"],
              f"retry: тип ошибки (получено {r['error'][:60]})")

    # ═══ 12. Retry: успех с 1-го раза — 1 вызов ═══
    _c12 = {"n": 0}
    def _success_once(*a, **kw):
        _c12["n"] += 1
        return fake_resp

    fc12 = MagicMock()
    fc12.responses.create.side_effect = _success_once
    with patch.object(llm, "_get_client", return_value=fc12):
        r = llm.call_alice_flash("i", "u")
        check("error" not in r, "retry: успех с 1-го раза")
        check(_c12["n"] == 1, f"retry: 1 вызов (получено {_c12['n']})")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()