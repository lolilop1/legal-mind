# -*- coding: utf-8 -*-
"""Интеграционные тесты Flask-приложения. LLM замокан, реальные API не вызываются."""

import _bootstrap  # noqa: F401

import os
import sys
import tempfile
from pathlib import Path


# ═══ Готовим окружение ДО импорта app.py ═══
_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["CASE_DB_PATH"] = _TMP_DB
os.environ["SECRET_KEY"] = "test-secret-not-for-prod"
os.environ["SESSION_COOKIE_SECURE"] = "false"


# Импортируем app и мокаем LLM
import web.app as app_module
import modules.consumer.engine as consumer_engine


# ─── Мок LLM ───
def _fake_call_llm_uk_noise(instructions, user_input):
    """Подменяет _call_llm в web/app.py для UK/шум."""
    if "тишин" in instructions or "участковому" in instructions.lower():
        return {"parsed": {
            "описание_проблемы_формальное": "Из вышерасположенной квартиры "
                "в ночное время доносится громкая музыка.",
        }}
    # UK по умолчанию
    return {"parsed": {
        "описание_проблемы_формальное": "В подъезде многоквартирного дома "
            "не производится уборка мест общего пользования.",
        "упоминание_повторного_обращения": "",
        "применимые_нормы": [
            "Статья 161 Жилищного кодекса РФ",
            "Постановление Правительства РФ от 13.08.2006 № 491",
            "Постановление Госстроя РФ от 27.09.2003 № 170",
        ],
    }}


def _fake_call_llm_consumer(instructions, user_input):
    """Подменяет _call_llm в modules/consumer/engine.py."""
    return {"parsed": {
        "описание_проблемы_формальное": "Приобретён товар, выявлен недостаток.",
        "требование": "Возвратить уплаченную за товар сумму",
        "применимые_нормы": [
            "Статья 18 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
            "Статья 22 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
        ],
    }}


app_module._call_llm = _fake_call_llm_uk_noise
consumer_engine._call_llm = _fake_call_llm_consumer


# ─── Фикстура клиента ───
app = app_module.app
app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False


# ═══ Утилиты ═══
UK_FORM = {
    "problem_type": "uk",
    "проблема": "в подъезде не убирают уже две недели, грязь и мусор",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "дата_начала": "около двух недель",
    "обращались_ранее": "нет",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
    "organization": "ООО «УК Тестовая»",
}

CONSUMER_FORM = {
    "problem_type": "consumer",
    "проблема": "купил смартфон Samsung, через неделю перестал работать",
    "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
    "продавец": "ООО «М.Видео»",
    "адрес_продавца": "125167, г. Москва, Ленинградский пр-т, д. 76А",
    "дата_покупки": "10.09.2026",
    "фио": "Иванов Иван Иванович",
    "телефон": "+7 999 123-45-67",
}


def _get_csrf(client):
    """Забирает CSRF-токен из формы (неявный GET /)."""
    import re as _re
    r = client.get("/")
    html = r.get_data(as_text=True)
    m = _re.search(r'name="_csrf_token"\s+value="([^"]+)"', html)
    return m.group(1) if m else ""


def _post_with_csrf(client, url, data, **kw):
    """POST с автоматическим CSRF-токеном."""
    data = dict(data)
    data["_csrf_token"] = _get_csrf(client)
    return client.post(url, data=data, **kw)


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

    client = app.test_client()

    # ═══ 1. Роуты GET ═══
    r = client.get("/")
    check(r.status_code == 200, "/: 200")
    check("Legal Mind" in r.get_data(as_text=True), "/: содержит 'Legal Mind'")

    r = client.get("/my")
    check(r.status_code == 200, "/my: 200")
    check("Мои дела" in r.get_data(as_text=True), "/my: заголовок")

    r = client.get("/health")
    check(r.status_code == 200, "/health: 200")
    j = r.get_json()
    check(j.get("status") == "ok", "/health: status=ok")
    check(j.get("llm_provider") == "alice-ai-flash", "/health: провайдер")

    # ═══ 2. /case/<invalid> → 404 ═══
    r = client.get("/case/invalid")
    check(r.status_code == 404, "GET /case/invalid → 404")
    r = client.get("/case/LM-20260101-0001-short")
    check(r.status_code == 404, "GET /case/<короткий uuid> → 404")
    r = client.get("/case/XXXX-not-a-case")
    check(r.status_code == 404, "GET /case/XXXX → 404")

    # ═══ 3. POST /submit UK — счастливый путь ═══
    r = _post_with_csrf(client, "/submit", UK_FORM, follow_redirects=False)
    check(r.status_code == 302, "POST /submit UK → 302 (redirect)")
    loc = r.headers.get("Location", "")
    check("/case/" in loc, f"POST /submit UK → redirect на /case/ ({loc[:60]})")
    check("just_created=1" in loc, "POST /submit UK → ?just_created=1")

    # Извлекаем case_ref
    case_ref = loc.split("/case/")[-1].split("?")[0]
    check(len(case_ref) > 30, f"case_ref длинный ({len(case_ref)} симв.)")

    # GET /case/<ref>
    r = client.get(f"/case/{case_ref}")
    check(r.status_code == 200, "GET /case/<ref> → 200")
    html = r.get_data(as_text=True)
    # В карточке: номер дела, тип (label из core/labels.py), source_text
    check("LM-" in html, "GET /case: номер дела в html")
    check("Жалоба в УК" in html, "GET /case: тип 'Жалоба в УК' (label)")
    check("подъезд" in html.lower() or "убор" in html.lower(),
          "GET /case: source_text сохранён")
    check("Версия документа" in html, "GET /case: блок версий")

    # GET PDF
    r = client.get(f"/case/{case_ref}/pdf/1")
    check(r.status_code == 200, "GET /case/<ref>/pdf/1 → 200")
    check(r.mimetype == "application/pdf", "PDF mimetype")
    check(r.data[:5] == b"%PDF-", "PDF заголовок %PDF-")

    # ═══ 4. Валидация: пустые поля ═══
    r = _post_with_csrf(client, "/submit", data={"problem_type": "uk"}, follow_redirects=False)
    check(r.status_code == 200, "POST с пустыми полями → 200 (не 302)")
    html = r.get_data(as_text=True)
    check("Проверьте форму" in html or "Заполните" in html,
          "POST с пустыми полями → показаны ошибки")

    # ═══ 5. Валидация: плохой телефон ═══
    bad = dict(UK_FORM)
    bad["телефон"] = "123"
    r = _post_with_csrf(client, "/submit", data=bad, follow_redirects=False)
    check(r.status_code == 200, "POST с плохим телефоном → 200")
    check("коротк" in r.get_data(as_text=True).lower()
          or "телефон" in r.get_data(as_text=True).lower(),
          "POST: ошибка про телефон")

    # ═══ 6. Consumer marketplace без номера заказа → блок ═══
    mp = dict(CONSUMER_FORM)
    mp["продавец"] = "Ozon"
    mp["адрес_продавца"] = ""
    r = _post_with_csrf(client, "/submit", data=mp, follow_redirects=False)
    check(r.status_code == 200, "POST marketplace без номера → 200 (не 302)")
    html = r.get_data(as_text=True)
    check("Номер заказа" in html or "номер заказа" in html.lower(),
          "POST marketplace: ошибка про номер заказа")

    # ═══ 7. IDOR-регресс через роут ═══
    # Создаём второй CASE
    r = _post_with_csrf(client, "/submit", UK_FORM, follow_redirects=False)
    case_ref2 = r.headers.get("Location", "").split("/case/")[-1].split("?")[0]
    check(case_ref2 != case_ref, "Второй POST создал другой CASE")
    # Пытаемся скачать doc_id=1 (принадлежит первому) через второй CASE
    r = client.get(f"/case/{case_ref2}/pdf/1")
    check(r.status_code == 404,
          "IDOR-регресс: чужой doc_id через свой case_ref → 404")

    # ═══ 7б. CSRF-защита ═══
    # POST без токена → 400
    r_no_csrf = client.post("/submit", data=UK_FORM, follow_redirects=False)
    check(r_no_csrf.status_code == 400,
          f"CSRF: POST без токена → 400 (получено {r_no_csrf.status_code})")
    html_no = r_no_csrf.get_data(as_text=True)
    check("Ошибка безопасности" in html_no or "подделан" in html_no,
          "CSRF: показана страница ошибки")

    # POST с чужим токеном → 400
    bad = dict(UK_FORM)
    bad["_csrf_token"] = "wrong-token-12345"
    r_bad = client.post("/submit", data=bad, follow_redirects=False)
    check(r_bad.status_code == 400, "CSRF: неверный токен → 400")

    # POST с валидным токеном → 302 (уже проверено выше, но подтвердим)
    tok = _get_csrf(client)
    good = dict(UK_FORM)
    good["_csrf_token"] = tok
    r_good = client.post("/submit", data=good, follow_redirects=False)
    check(r_good.status_code == 302, "CSRF: валидный токен → 302")

    # Токен появляется в форме GET /
    r_form = client.get("/")
    check('name="_csrf_token"' in r_form.get_data(as_text=True),
          "CSRF: скрытое поле в форме есть")

    # ═══ 8. Удаляем временную БД ═══
    try:
        os.unlink(_TMP_DB)
    except OSError:
        pass

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()