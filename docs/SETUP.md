# Legal Mind — Setup

Инструкция развернуть проект локально и на сервере.

## Требования

- Python 3.10+
- Git
- Шрифт с кириллицей (Arial на Windows/macOS, DejaVu на Linux)
- API-ключ Yandex Cloud
- Доступ к интернету для LLM

## Из Yandex Cloud нужно

- API-ключ сервисного аккаунта с ролью ai.languageModels.user
- Folder ID

Ключи в web/.env:
YANDEX_API_KEY, YANDEX_FOLDER_ID, AI_STUDIO_INDEX_ID, SECRET_KEY.

SECRET_KEY генерируется: python -c "import secrets; print(secrets.token_hex(32))"

## Локальная установка

1. Клонирование: git clone <repo> legal_mind && cd legal_mind

2. Виртуальное окружение:
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   (если политика блокирует: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)

3. Зависимости:
   cd web
   pip install -r requirements.txt

4. .env:
   Copy-Item web\.env.example web\.env
   Заполнить 4 ключа.

5. База CASE создастся автоматически в web/cases.db.

6. Тесты:
   cd ..
   python tests\run_all.py
   Ожидание: 10 файлов, 196 проверок, упало 0.

7. Запуск:
   cd web
   python app.py
   Открыть http://127.0.0.1:5000/

## Установка на сервер

1. Ubuntu 22.04/24.04:
   apt update && apt upgrade -y
   apt install -y python3 python3-pip python3-venv nginx git fonts-dejavu

2. Пользователь:
   useradd -m -s /bin/bash legal
   mkdir -p /opt/legal_mind
   chown legal:legal /opt/legal_mind

3. Заливка (с локальной машины):
   scp -r core region modules web deploy root@201.24.49.121:/opt/legal_mind/

4. Права:
   cd /opt/legal_mind
   chown -R legal:legal .
   chmod 600 web/.env
   chmod 755 core region modules web deploy
   chmod -R 755 web/static

5. Venv:
   sudo -u legal python3 -m venv venv
   sudo -u legal ./venv/bin/pip install -r web/requirements.txt

6. systemd:
   cp deploy/legal-mind.service /etc/systemd/system/
   systemctl daemon-reload
   systemctl enable legal-mind
   systemctl start legal-mind

7. nginx:
   cp deploy/nginx.conf /etc/nginx/sites-available/legal-mind
   ln -sf /etc/nginx/sites-available/legal-mind /etc/nginx/sites-enabled/
   rm -f /etc/nginx/sites-enabled/default
   nginx -t && systemctl reload nginx

8. Проверка:
   curl http://127.0.0.1:5000/health

## Деплой после правок

.\deploy\deploy.ps1

Скрипт: тесты → бэкап → заливка → перезапуск → health → откат при провале.

## Полезные команды

Логи: journalctl -u legal-mind -n 100
Перезапуск: systemctl restart legal-mind
Статистика БД: см. deploy.md

## Возможные проблемы

ModuleNotFoundError — запуск не из корня.

fpdf2 ошибка — pip install --upgrade fpdf2.

Permission denied на CSS — chmod 755 web/static.

llm_configured: false — проверить cat /opt/legal_mind/web/.env.

## Что дальше

README.md, docs/ARCHITECTURE.md, docs/MODULES.md, docs/DECISIONS.md.