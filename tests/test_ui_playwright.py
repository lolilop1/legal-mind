# -*- coding: utf-8 -*-
"""UI smoke через Playwright (headless Chromium).

Поднимает Flask в фоновом thread (не subprocess — чтобы мокать LLM),
открывает страницы, тыкает как юзер.

Покрыто:
- главная рендерится
- wizard: шаг 1 -> шаг 2 -> шаг 3
- показ/скрытие consumer-полей
- marketplace: Ozon -> поле "Номер заказа", скрытие ссылки
- календари (Air Datepicker) открываются: дата покупки + дата обращения
- inline-ошибки (.lm-field-error) при пустых полях
"""

import _bootstrap  # noqa: F401

import os
import sys
import tempfile
import threading
import time


_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["CASE_DB_PATH"] = _TMP_DB
os.environ["SECRET_KEY"] = "ui-test-secret"
os.environ["SESSION_COOKIE_SECURE"] = "false"


import web.app as app_module
import modules.consumer.engine as consumer_engine


# ─── Мок LLM (не пригодится — но пусть будет) ───
def _fake_uk_noise(instructions, user_input):
    return {"parsed": {
        "описание_проблемы_формальное": "тест",
        "упоминание_повторного_обращения": "",
        "применимые_нормы": [
            "Статья 161 Жилищного кодекса РФ",
            "Постановление Правительства РФ от 13.08.2006 № 491",
            "Постановление Госстроя РФ от 27.09.2003 № 170",
        ],
    }}


def _fake_consumer(instructions, user_input):
    return {"parsed": {
        "описание_проблемы_формальное": "тест",
        "требование": "вернуть деньги",
        "применимые_нормы": [
            "Статья 18 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
        ],
    }}


app_module._call_llm = _fake_uk_noise
consumer_engine._call_llm = _fake_consumer


app = app_module.app
_PORT = 5002
_BASE = f"http://127.0.0.1:{_PORT}"


def _start_flask():
    """Flask в daemon-thread, threaded=True — иначе Playwright заблокирует."""
    t = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=_PORT,
                               threaded=True, use_reloader=False),
        daemon=True,
    )
    t.start()
    # Ждём поднятия
    import urllib.request
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{_BASE}/health", timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    # Graceful skip если Playwright не установлен
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP: Playwright не установлен.")
        print("      Установка: python -m pip install playwright && python -m playwright install chromium")
        # exit 0 — это не fail, CI поставит playwright отдельным шагом
        return 0

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

    if not _start_flask():
        print("FAIL: Flask не поднялся на :5002")
        return 1
    print("OK: Flask запущен\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        # ═══ 1. Главная рендерится ═══
        page.goto(_BASE, wait_until="networkidle")
        html = page.content()
        check("Legal Mind" in html, "UI: главная содержит 'Legal Mind'")
        check(page.locator("select[name='problem_type']").count() == 1,
              "UI: dropdown типа проблемы")
        check(page.locator("textarea[name='проблема']").count() == 1,
              "UI: textarea проблемы")
        check(page.locator(".wizard-progress-step").count() == 3,
              "UI: 3 шага в прогресс-баре")

        # ═══ 2. Шаг 1 → шаг 2 (UK) ═══
        page.fill("textarea[name='проблема']",
                  "в подъезде не убирают две недели, мусор и грязь")
        page.click("button.wizard-next")
        time.sleep(0.3)
        check(page.locator(".wizard-step[data-step='2']").is_visible(),
              "UI: шаг 2 показан после клика 'Далее'")
        check(page.locator("#uk-noise-fields").is_visible(),
              "UI: UK-поля видны (тип=uk по умолчанию)")
        check(page.locator("#consumer-only-fields").is_hidden(),
              "UI: consumer-поля скрыты (тип=uk)")

        # ═══ 3. Возврат на шаг 1, смена на consumer ═══
        page.click("button.wizard-prev")
        time.sleep(0.3)
        page.select_option("select[name='problem_type']", "consumer")
        time.sleep(0.2)
        page.click("button.wizard-next")
        time.sleep(0.3)
        check(page.locator("#consumer-only-fields").is_visible(),
              "UI: consumer-поля показаны (тип=consumer)")
        check(page.locator("#uk-noise-fields").is_hidden(),
              "UI: UK-поля скрыты (тип=consumer)")

        # ═══ 4. Marketplace (Ozon) → поле "Номер заказа" ═══
        page.fill("input[name='продавец']", "Ozon")
        page.dispatch_event("input[name='продавец']", "input")
        time.sleep(0.3)
        check(page.locator("#order-number-field").is_visible(),
              "UI: Ozon → поле 'Номер заказа' показано")
        check(page.locator("#seller-link-field").is_hidden(),
              "UI: Ozon → поле 'Ссылка' скрыто")

        # ═══ 5. Обычный продавец → ссылка показана, номер скрыт ═══
        page.fill("input[name='продавец']", "Мария Петрова")
        page.dispatch_event("input[name='продавец']", "input")
        time.sleep(0.3)
        check(page.locator("#order-number-field").is_hidden(),
              "UI: физлицо → поле 'Номер заказа' скрыто")
        check(page.locator("#seller-link-field").is_visible(),
              "UI: физлицо → поле 'Ссылка' показано")

        # ═══ 6. Календарь дата покупки ═══
        page.click("input[name='дата_покупки']")
        time.sleep(0.4)
        check(page.locator(".air-datepicker.-active-").count() > 0,
              "UI: календарь 'Дата покупки' открывается")

        # Закрываем календарь (Escape)
        page.keyboard.press("Escape")
        time.sleep(0.2)

        # ═══ 7. Календарь дата обращения ═══
        page.click("input[name='дата_обращения']")
        time.sleep(0.4)
        check(page.locator(".air-datepicker.-active-").count() > 0,
              "UI: календарь 'Дата обращения' открывается (был баг!)")

        page.keyboard.press("Escape")
        time.sleep(0.2)

        # ═══ 8. Inline-ошибки при пустом поле ═══
        page.goto(_BASE, wait_until="networkidle")
        page.click("button.wizard-next")  # пустая textarea
        time.sleep(0.3)
        check(page.locator(".lm-field-error").count() > 0,
              "UI: inline-ошибка при пустом описании")
        check(page.locator(".lm-field-error").first.is_visible(),
              "UI: inline-ошибка видима")

        # CSS стиль подхватился?
        err_style = page.evaluate('''() => {
            const el = document.querySelector('.lm-field-error');
            if (!el) return null;
            const s = getComputedStyle(el);
            return {color: s.color, display: s.display};
        }''')
        check(err_style is not None and "rgb(211, 47, 47)" in err_style["color"],
              f"UI: .lm-field-error красный (got: {err_style})")

        # ═══ 8б. Поля 'Текущая цена' и 'Номер заказа' ═══
        page.goto(_BASE, wait_until="networkidle")
        page.select_option("select[name='problem_type']", "consumer")
        time.sleep(0.2)
        page.fill("textarea[name='проблема']",
                  "купил смартфон, сломался, хочу вернуть деньги")
        page.click("button.wizard-next")
        time.sleep(0.3)

        # Текущая цена — в consumer-блоке
        check(page.locator("input[name='текущая_цена']").count() == 1,
              "UI: поле 'Текущая цена' в форме")
        # Номер заказа скрыт (не маркетплейс)
        check(page.locator("#order-number-field").is_hidden(),
              "UI: 'Номер заказа' скрыт (не маркетплейс)")

        # Меняем на Ozon → номер заказа виден
        page.fill("input[name='продавец']", "Ozon")
        page.dispatch_event("input[name='продавец']", "input")
        time.sleep(0.3)
        check(page.locator("#order-number-field").is_visible(),
              "UI: Ozon -> 'Номер заказа' показан")

        # ═══ 9. Стили CSS загрузились ═══
        css_ok = page.evaluate('''() => {
            const s = document.querySelector('.container');
            if (!s) return false;
            const st = getComputedStyle(s);
            return st.maxWidth === '680px';
        }''')
        check(css_ok, "UI: style.css загружен (container max-width)")

        browser.close()

    # cleanup
    try:
        os.unlink(_TMP_DB)
    except OSError:
        pass

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())