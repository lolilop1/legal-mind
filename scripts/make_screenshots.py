"""Делает скриншоты ключевых экранов через Playwright (headless).

Запуск: python scripts/make_screenshots.py
Результат: tests/screenshots/*.png

Экраны:
1. Главная (шаг 1 wizard) — desktop
2. Шаг 2 consumer (все поля) — desktop
3. Шаг 3 (чекбокс 152-ФЗ) — desktop
4. Карточка дела (с расчётом неустойки) — desktop
5. Мобильная главная — 375px
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from pathlib import Path


_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tests"))

os.environ["CASE_DB_PATH"] = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["SECRET_KEY"] = "screenshot-secret"

import web.app as app_module
import modules.consumer.engine as consumer_engine


# Замоканный LLM — чтобы не тратить деньги
def _fake_uk_noise(inst, usr):
    return {"parsed": {
        "описание_проблемы_формальное": "тест",
        "упоминание_повторного_обращения": "",
        "применимые_нормы": [
            "Статья 161 Жилищного кодекса РФ",
            "Постановление Правительства РФ от 13.08.2006 № 491",
            "Постановление Госстроя РФ от 27.09.2003 № 170",
        ],
    }}


def _fake_consumer(inst, usr):
    return {"parsed": {
        "описание_проблемы_формальное": "Приобретён смартфон Samsung, "
            "выявлен недостаток — устройство перестало работать.",
        "требование": "Возвратить уплаченную за товар сумму",
        "применимые_нормы": [
            "Статья 18 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
            "Статья 22 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей»",
        ],
    }}


app_module._call_llm = _fake_uk_noise
consumer_engine._call_llm = _fake_consumer

app = app_module.app
_PORT = 5003
_BASE = f"http://127.0.0.1:{_PORT}"

OUT = _ROOT / "tests" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)


def _click_visible(page, selector: str, timeout: int = 5000) -> None:
    """Кликает по ВИДИМОМУ элементу (первый скрытый игнорирует)."""
    loc = page.locator(selector)
    count = loc.count()
    for i in range(count):
        el = loc.nth(i)
        if el.is_visible():
            el.click()
            return
    raise RuntimeError(f"Не найден видимый элемент: {selector}")


def _start_flask():
    t = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=_PORT,
                               threaded=True, use_reloader=False),
        daemon=True,
    )
    t.start()
    import urllib.request
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{_BASE}/health", timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def main() -> int:
    from playwright.sync_api import sync_playwright

    if not _start_flask():
        print("FAIL: Flask не поднялся")
        return 1

    print(f"OK: Flask на {_BASE}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ═══ Desktop 1280x900 ═══
        ctx = browser.new_context(viewport={"width": 1280, "height": 900},
                                  device_scale_factor=2)
        page = ctx.new_page()

        # 1. Главная
        page.goto(_BASE, wait_until="networkidle")
        page.screenshot(path=str(OUT / "01_home_step1.png"), full_page=True)
        print(f"OK: 01_home_step1.png")

        # 2. Consumer-поля на шаге 2
        page.select_option("select[name='problem_type']", "consumer")
        time.sleep(0.2)
        page.fill("textarea[name='проблема']",
                  "купил в М.Видео смартфон Samsung, через неделю перестал включаться")
        _click_visible(page, "button.wizard-next")
        time.sleep(0.4)
        # Заполним некоторые поля чтобы видно было
        page.fill("input[name='адрес']", "г. Москва, ул. Ленина, д. 15, кв. 42")
        page.fill("input[name='продавец']", "ООО «М.Видео»")
        page.dispatch_event("input[name='продавец']", "input")
        time.sleep(0.2)
        page.fill("input[name='адрес_продавца']", "125167, г. Москва, Ленинградский пр-т, д. 76А")
        page.fill("input[name='цена']", "50000")
        page.fill("input[name='текущая_цена']", "60000")
        page.fill("input[name='дата_обращения']", "01.08.2026")
        time.sleep(0.2)
        # НЕ кликаем по календарю — просто скрин формы
        # Закрываем календарь если случайно открылся
        page.keyboard.press("Escape")
        time.sleep(0.2)
        page.screenshot(path=str(OUT / "02_step2_consumer.png"), full_page=True)
        print(f"OK: 02_step2_consumer.png")

        # Отдельный скрин с открытым календарём
        page.click("input[name='дата_покупки']")
        time.sleep(0.5)
        page.screenshot(path=str(OUT / "02b_calendar_open.png"), full_page=True)
        print(f"OK: 02b_calendar_open.png")
        page.keyboard.press("Escape")
        time.sleep(0.2)

        # 3. Шаг 3 — чекбокс
        _click_visible(page, "button.wizard-next")
        time.sleep(0.4)
        page.screenshot(path=str(OUT / "03_step3_consent.png"), full_page=True)
        print(f"OK: 03_step3_consent.png")

        # 4. Карточка дела с расчётом
        page.fill("input[name='фио']", "Иванов Иван Иванович")
        page.fill("input[name='телефон']", "+7 999 123-45-67")
        page.check("input[name='privacy_consent']")
        time.sleep(0.3)
        _click_visible(page, "button.wizard-submit")
        time.sleep(2)
        page.screenshot(path=str(OUT / "04_case_card.png"), full_page=True)
        print(f"OK: 04_case_card.png")

        ctx.close()

        # ═══ Mobile 375x812 (iPhone X) ═══
        mob = browser.new_context(viewport={"width": 375, "height": 812},
                                  device_scale_factor=2, is_mobile=True)
        mp = mob.new_page()
        mp.goto(_BASE, wait_until="networkidle")
        mp.screenshot(path=str(OUT / "05_mobile_home.png"), full_page=True)
        print(f"OK: 05_mobile_home.png")

        mp.select_option("select[name='problem_type']", "consumer")
        time.sleep(0.2)
        mp.fill("textarea[name='проблема']",
                "купил смартфон, сломался, хочу вернуть")
        _click_visible(mp, "button.wizard-next")
        time.sleep(0.4)
        mp.screenshot(path=str(OUT / "06_mobile_step2.png"), full_page=True)
        print(f"OK: 06_mobile_step2.png")

        mob.close()
        browser.close()

    print(f"\nВсе скриншоты в: {OUT}")
    print("Открой и посмотри глазами.")
    return 0


if __name__ == "__main__":
    sys.exit(main())