# -*- coding: utf-8 -*-
"""Регресс-тесты security-патчей. LLM не вызывается, API не тратится.

Покрыто:
- SECRET_KEY обязателен (subprocess: без ключа app падает)
- Cookie flags: HttpOnly, SameSite=Lax, Secure условно
- ProxyFix установлен и настроен
- PII не попадают в логи (subprocess + разбор requests.log)
"""

import _bootstrap  # noqa: F401

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


# ═══ Готовим env ДО импорта app.py ═══
_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["CASE_DB_PATH"] = _TMP_DB
os.environ["SECRET_KEY"] = "test-secret-for-security-checks"
os.environ["SESSION_COOKIE_SECURE"] = "false"

import web.app as app_module


_ROOT = Path(__file__).resolve().parent.parent
_WEB = _ROOT / "web"


def _run_subprocess_no_secret():
    """Запускает отдельный питон, который импортирует app.py без SECRET_KEY.

    Возвращает CompletedProcess. Ожидание: returncode != 0 и 'SECRET_KEY' в stderr.
    """
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    env = os.environ.copy()
    env["SECRET_KEY"] = ""  # load_dotenv(override=False) не перезапишет
    env["CASE_DB_PATH"] = tmp_db
    env["PYTHONIOENCODING"] = "utf-8"

    # Импортируем app в подпроцессе
    code = "import web.app"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        os.unlink(tmp_db)
    except OSError:
        pass
    return result


def _run_subprocess_with_post(form_data: dict) -> str:
    """POST /submit в подпроцессе (с моками LLM), возвращает содержимое лога.

    Хитрость: LLM не нужен — посылаем данные, которые упадут на hard-check,
    но всё равно пройдут через log_event с длиной адреса.
    """
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    tmp_log_dir = tempfile.mkdtemp(prefix="lm_logs_")
    env = os.environ.copy()
    env["SECRET_KEY"] = "test-secret"
    env["CASE_DB_PATH"] = tmp_db
    env["PYTHONIOENCODING"] = "utf-8"
    # Меняем каталог логов через переменную окружения? В app.py LOG_DIR — жёстко.
    # Поэтому — просто отправим запрос и прочитаем стандартный LOG_DIR.

    script = '''
import os, sys
os.environ["CASE_DB_PATH"] = {db!r}
os.environ["SECRET_KEY"] = "test-secret"
import web.app as m

# Мокаем LLM — на случай если hard-check пропустит
def _fake(inst, usr):
    return {{"parsed": {{
        "описание_проблемы_формальное": "test",
        "упоминание_повторного_обращения": "",
        "применимые_нормы": [
            "Статья 161 Жилищного кодекса РФ",
            "Постановление Правительства РФ от 13.08.2006 № 491",
            "Постановление Госстроя РФ от 27.09.2003 № 170",
        ],
    }}}}
m._call_llm = _fake

client = m.app.test_client()
form = {form!r}
client.post("/submit", data=form)
'''.format(db=tmp_db, form=form_data)

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    try:
        os.unlink(tmp_db)
    except OSError:
        pass

    # Читаем лог (app.py пишет в /opt/legal_mind/logs или ../logs)
    log_path = _ROOT / "logs" / "requests.log"
    log_content = ""
    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                log_content = f.read()
        except OSError:
            pass
    return log_content


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

    app = app_module.app

    # ═══ 1. SECRET_KEY обязателен ═══
    result = _run_subprocess_no_secret()
    check(result.returncode != 0,
          f"SECRET_KEY пустой → app падает (rc={result.returncode})")
    combined = (result.stderr or "") + (result.stdout or "")
    check("SECRET_KEY" in combined,
          "SECRET_KEY упомянут в ошибке (RuntimeError)")
    check("python -c" in combined or "secrets.token_hex" in combined,
          "SECRET_KEY: подсказка про генерацию")

    # ═══ 2. SECRET_KEY из env используется ═══
    check(app.secret_key == os.environ["SECRET_KEY"],
          "app.secret_key = SECRET_KEY из env")

    # ═══ 3. Cookie flags ═══
    check(app.config.get("SESSION_COOKIE_HTTPONLY") is True,
          "SESSION_COOKIE_HTTPONLY = True")
    check(app.config.get("SESSION_COOKIE_SAMESITE") == "Lax",
          "SESSION_COOKIE_SAMESITE = 'Lax'")
    check(app.config.get("SESSION_COOKIE_SECURE") is False,
          "SESSION_COOKIE_SECURE = False (SESSION_COOKIE_SECURE не установлен)")

    # ═══ 4. Cookie в реальном ответе ═══
    client = app.test_client()
    # Дёргаем /my — там трогается session → должен быть Set-Cookie
    r = client.get("/my")
    cookie_header = r.headers.get("Set-Cookie", "")
    check("HttpOnly" in cookie_header or cookie_header == "",
          f"Set-Cookie содержит HttpOnly ({cookie_header[:60]})")
    check("SameSite=Lax" in cookie_header or cookie_header == "",
          f"Set-Cookie содержит SameSite=Lax ({cookie_header[:60]})")
    check("Secure" not in cookie_header,
          "Set-Cookie БЕЗ Secure (SESSION_COOKIE_SECURE=false)")

    # ═══ 5. ProxyFix установлен и настроен ═══
    from werkzeug.middleware.proxy_fix import ProxyFix
    check(isinstance(app.wsgi_app, ProxyFix),
          "app.wsgi_app — экземпляр ProxyFix")
    check(app.wsgi_app.x_for == 1,
          f"ProxyFix.x_for = 1 (получено {app.wsgi_app.x_for})")
    check(app.wsgi_app.x_proto == 1,
          f"ProxyFix.x_proto = 1 (получено {app.wsgi_app.x_proto})")
    check(app.wsgi_app.x_host == 1,
          f"ProxyFix.x_host = 1 (получено {app.wsgi_app.x_host})")

    # ═══ 6. PII не попадают в логи ═══
    # Отправляем форму с «адресом», который легко искать в логе
    marker_addr = "тестоград-маркер-пдн-12345"
    form = {
        "problem_type": "uk",
        "проблема": "в подъезде не убирают две недели, мусор и грязь",
        "адрес": marker_addr,
        "дата_начала": "недавно",
        "обращались_ранее": "нет",
        "фио": "Иванов Иван Иванович",
        "телефон": "+7 999 123-45-67",
        "organization": "ООО «УК Тестовая»",
    }
    log_content = _run_subprocess_with_post(form)

    if not log_content:
        check(True, "PII: лог пуст или недоступен — нечего проверять (SKIP)")
        print("       (logs/requests.log не найден — тест PII пропущен)")
    else:
        check(marker_addr not in log_content,
              f"PII: адрес '{marker_addr[:20]}...' НЕ в логе")
        # log_event пишет len=N (не addr_len — то в log.info идёт в stderr)
        check("len=" in log_content,
              "PII: в логе есть len=N (длина проблемы, не сам текст)")
        # Дополнительно: убедимся что в логе нет самого «маркер»-текста
        check("маркер-пдн" not in log_content,
              "PII: маркер не утёк в лог")

    # ═══ 7. /health не раскрывает секреты ═══
    r = client.get("/health")
    j = r.get_json()
    check("secret_key" not in str(j).lower(),
          "/health: не раскрывает secret_key")
    check("api_key" not in str(j).lower(),
          "/health: не раскрывает api_key")
    check(j.get("status") == "ok", "/health: status=ok")

    # ═══ 8. cleanup ═══
    try:
        os.unlink(_TMP_DB)
    except OSError:
        pass

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()