# -*- coding: utf-8 -*-
"""Smoke-test: прогон 6 сценариев локально, без ручного тыканья форм.

Что делает:
  1. Поднимает Flask на 127.0.0.1:5001 (отдельная БД — прод не пачкается)
  2. Отправляет 6 реалистичных кейсов (UK, шум, 4 consumer-сценария)
  3. Скачивает PDF, проверяет %PDF-заголовок
  4. Открывает все PDF разом

Запуск:  python scripts\\smoke_test.py
"""

import os
import re
import sys
import subprocess
import time
from pathlib import Path

# ─── UTF-8 на Windows ───
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_ROOT = Path(__file__).resolve().parent.parent
_WEB = _ROOT / "web"
_OUT = _ROOT / "smoke_output"
_PORT = 5001
_BASE = f"http://127.0.0.1:{_PORT}"


# ═══ Кейсы ═══

CASES = [
    ("uk_uborka", {
        "problem_type": "uk",
        "проблема": "В подъезде не убирают уже две недели, грязь и мусор в углах",
        "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
        "дата_начала": "около двух недель назад",
        "обращались_ранее": "да, 01.08.2026, ответа не было",
        "фио": "Иванов Иван Иванович",
        "телефон": "+7 999 123-45-67",
        "organization": "ООО «УК Жилищник-1»",
    }),
    ("noise_music", {
        "problem_type": "noise",
        "проблема": "Сосед сверху громко слушает музыку по ночам, не даёт спать",
        "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
        "дата_начала": "месяц назад",
        "обращались_ранее": "нет",
        "фио": "Иванов Иван Иванович",
        "телефон": "+7 999 123-45-67",
        "organization": "Начальнику ОВД по Тверскому району",
    }),
    ("consumer_defect_calc", {
        "problem_type": "consumer",
        "проблема": "Купил смартфон Samsung, через неделю перестал работать. Продавец отказывается возвращать деньги",
        "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
        "продавец": "ООО «М.Видео»",
        "адрес_продавца": "125167, г. Москва, Ленинградский пр-т, д. 76А",
        "дата_покупки": "10.08.2026",
        "цена": "50000",
        "дата_обращения": "01.09.2026",
        "фио": "Иванов Иван Иванович",
        "телефон": "+7 999 123-45-67",
    }),
    ("consumer_return14", {
        "problem_type": "consumer",
        "проблема": "Купила куртку, не подошёл размер, хочу вернуть деньги",
        "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
        "продавец": "ООО «Модный Магазин»",
        "адрес_продавца": "г. Москва, ул. Тверская, д. 1",
        "дата_покупки": "10.09.2026",
        "цена": "15000",
        "фио": "Иванова Мария Петровна",
        "телефон": "+7 999 123-45-67",
    }),
    ("consumer_marketplace", {
        "problem_type": "consumer",
        "проблема": "Заказал на Ozon телефон, пришёл с трещиной на экране, хочу вернуть деньги",
        "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
        "продавец": "Ozon",
        "номер_заказа": "12345678-1234",
        "дата_покупки": "01.09.2026",
        "цена": "30000",
        "дата_обращения": "05.09.2026",
        "фио": "Иванов Иван Иванович",
        "телефон": "+7 999 123-45-67",
    }),
    ("consumer_service_deadline", {
        "problem_type": "consumer",
        "проблема": "Заказал ремонт квартиры, обещали за 2 недели, делают третий месяц, сроки нарушены",
        "адрес": "г. Москва, ул. Ленина, д. 15, кв. 42",
        "продавец": "ООО «РемСтрой»",
        "адрес_продавца": "г. Москва, ул. Строителей, д. 5",
        "цена": "80000",
        "дата_обращения": "01.08.2026",
        "фио": "Иванов Иван Иванович",
        "телефон": "+7 999 123-45-67",
    }),
]


def _wait_health(timeout: int = 30) -> bool:
    import urllib.request
    for _ in range(timeout):
        try:
            with urllib.request.urlopen(f"{_BASE}/health", timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def _open_pdf(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass


def main() -> int:
    import urllib.request
    import urllib.parse
    import http.cookiejar

    _OUT.mkdir(exist_ok=True)
    log_path = _OUT / "flask.log"

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["SECRET_KEY"] = "smoke-test-not-for-prod"
    env["CASE_DB_PATH"] = str(_OUT / "smoke_cases.db")
    env["SESSION_COOKIE_SECURE"] = "false"

    print(f"Запускаю Flask на {_BASE} ...")
    log_file = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-c",
         "import app; app.app.run(host='127.0.0.1', port=5001, "
         "use_reloader=False, threaded=True)"],
        cwd=str(_WEB),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    if not _wait_health():
        print(f"FAIL: сервер не поднялся за 30 сек. Смотри {log_path}")
        proc.kill()
        log_file.close()
        return 1

    print("OK: сервер запущен\n")

    # Cookie-jar для сессии (чтобы CASE попадал в /my)
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    passed = 0
    failed = 0
    pdfs = []

    for i, (label, data) in enumerate(CASES, 1):
        print(f"[{i}/{len(CASES)}] {label}")
        body = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(
            f"{_BASE}/submit",
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        try:
            resp = opener.open(req, timeout=120)
        except urllib.error.HTTPError as e:
            print(f"  FAIL: HTTP {e.code}")
            failed += 1
            continue
        except Exception as e:
            print(f"  FAIL: {type(e).__name__}: {e}")
            failed += 1
            continue

        content = resp.read()
        url = resp.geturl()
        status = resp.status

        pdf_data = None
        # Вариант 1: редирект на /case/<ref>?just_created=1
        if "case" in url and status == 200:
            text = content.decode("utf-8", errors="replace")
            m = re.search(r"/case/([^/\"']+)/pdf/(\d+)", text)
            if m:
                case_ref, doc_id = m.group(1), m.group(2)
                try:
                    r2 = opener.open(f"{_BASE}/case/{case_ref}/pdf/{doc_id}", timeout=30)
                    pdf_data = r2.read()
                except Exception as e:
                    print(f"  FAIL: PDF-запрос упал: {e}")
                    failed += 1
                    continue

        # Вариант 2: PDF прямо в ответе (fallback без CASE)
        if pdf_data is None and content[:5] == b"%PDF-":
            pdf_data = content

        if pdf_data is None:
            print(f"  FAIL: ни PDF, ни /case (status={status}, url={url[:80]})")
            failed += 1
            continue

        if pdf_data[:5] != b"%PDF-":
            print(f"  FAIL: не PDF (заголовок: {pdf_data[:20]!r})")
            failed += 1
            continue

        out_path = _OUT / f"{i:02d}_{label}.pdf"
        out_path.write_bytes(pdf_data)
        size_kb = len(pdf_data) // 1024
        print(f"  OK: {out_path.name} ({size_kb} КБ)")
        pdfs.append(out_path)
        passed += 1

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    log_file.close()

    print()
    print("=" * 55)
    print(f"ИТОГО: {passed}/{len(CASES)} passed, {failed} failed")
    print(f"PDF:   {_OUT}")
    print(f"Лог:   {log_path}")
    print("=" * 55)

    if pdfs:
        print("\nОткрываю PDF...")
        for p in pdfs:
            _open_pdf(p)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())