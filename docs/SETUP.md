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

SECRET_KEY генерируется:
python -c "import secrets; print(secrets.token_hex(32))"

## Локальная установка

1. Клонирование:
   git clone https://github.com/lolilop1/legal-mind.git
   cd legal-mind

2. Виртуальное окружение:
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   (если политика блокирует:
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)

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
   Ожидание: 15 файлов, 305 проверок, упало 0.

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

3. Заливка — через git (автодеплой):
   git push origin main
   → GitHub Actions → SSH на сервер → git pull → restart

   Первый раз (с сервера): git clone git@github.com:lolilop1/legal-mind.git /opt/legal_mind

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

## Автодеплой (после первого ручного развёртывания)

1. Git на сервере:
   cd /opt/legal_mind
   git init
   git remote add origin git@github.com:lolilop1/legal-mind.git
   git fetch origin main
   git reset --hard origin/main

2. Deploy Key (read-only) в GitHub:
   - Settings → Deploy keys → Add deploy key
   - Вставить публичный ключ с сервера
   - Allow write access — НЕ ставить

3. SSH config на сервере:
   cat > ~/.ssh/config <<EOF
   Host github.com
     HostName github.com
     User git
     IdentityFile ~/.ssh/github_deploy_key
     IdentitiesOnly yes
   EOF
   chmod 600 ~/.ssh/config

4. GitHub Secrets (Settings → Secrets → Actions):
   - SSH_HOST=201.24.49.121
   - SSH_USER=root
   - SSH_PRIVATE_KEY=<приватный ключ>

5. Проверка:
   ssh -T git@github.com
   Ожидание: Hi lolilop1/legal-mind! You've successfully authenticated.

6. После этого — любой git push автоматически деплоит.

## Smoke-тест (локальный прогон 6 сценариев)

Одна команда — поднимает Flask на 127.0.0.1:5001 (отдельная БД, прод
не трогает), прогоняет 6 реалистичных кейсов (UK, шум, 4 consumer-
сценария), сохраняет PDF и открывает их разом:

    python scripts\smoke_test.py

Результат:
- `smoke_output/01_uk_uborka.pdf` … `06_consumer_service_deadline.pdf`
- `smoke_output/flask.log` — если что-то упало
- `smoke_output/smoke_cases.db` — изолированная БД

Занимает ~1-2 минуты (6 LLM-запросов к Alice AI Flash).

## Полезные команды

Логи приложения:
journalctl -u legal-mind -n 100 --no-pager

Статистика БД:
sudo -u legal /opt/legal_mind/venv/bin/python -c "
import sys
sys.path.insert(0, '/opt/legal_mind')
from core import case_db
case_db.init_db()
print(case_db.stats())
"

Перезапуск:
systemctl restart legal-mind

## Возможные проблемы

ModuleNotFoundError: No module named 'core'
— приложение запускается не из корня. Запускать из корня проекта.

fpdf2: not enough horizontal space
— pip install --upgrade fpdf2

Permission denied на CSS
— chmod 755 /opt/legal_mind/web/static

llm_configured: false
— cat /opt/legal_mind/web/.env — проверить 4 ключа

500 в карточке дела
— journalctl -u legal-mind -n 50 — там traceback

GitHub Actions: Permission denied (publickey)
— в SSH_PRIVATE_KEY вставлен не тот ключ. Должен быть локальный
  ~/.ssh/github_deploy_key (не серверный).

## Обновление базы регионов

cd /opt/legal_mind
python scripts/rag_mass_v4.py        (полный прогон, ~380 ₽)
python scripts/rag_hardcode_fixed.py (12 регионов ручной правки)
python scripts/build_embeddings.py   (пересборка эмбеддингов, ~5 ₽)

## Что дальше

- README.md — обзор проекта
- ROADMAP.md — план на этапы
- docs/ARCHITECTURE.md — как устроено
- docs/MODULES.md — что умеет
- docs/DECISIONS.md — журнал решений