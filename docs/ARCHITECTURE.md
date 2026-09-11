# Legal Mind — Architecture

## Высокоуровневая схема

Пользователь (браузер, телефон)
        |
        v
[nginx] — HTTPS, статика, reverse proxy
        |
        v
[gunicorn, 2 воркера] — WSGI
        |
        v
[Flask, web/app.py]
        |
        |— Валидация: телефон, ФИО, поля формы
        |— Hard-check: экстренность, маршрутизация, длина
        |— LLM (Alice AI Flash): нормализация текста
        |— Entity check: проверка, что ничего не потеряно
        |— Pre-check: что знаем / чего не хватает
        |— [Модуль 3]: определение региона + чтение закона
        |— Legal Trace: факт → квалификация → норма → источник
        |— PDF: fpdf2 + версия в подвале
        |
        v
CASE сохраняется в SQLite (web/cases.db)
        |
        v
PDF отдаётся пользователю

## Структура папок

legal_mind/
├── core/                    — общий код
│   ├── llm.py              — клиент Alice AI Flash
│   ├── name_declension.py  — склонение ФИО (pymorphy3)
│   ├── phone_check.py      — валидация телефона
│   ├── case_db.py          — доступ к БД CASE
│   ├── case_id.py          — генератор номера + UUID
│   ├── labels.py           — русские названия типов
│   ├── address.py          — нормализация адреса
│   ├── pre_checks.py       — модель PreCheckReport
│   └── trace.py            — модель LegalTrace
│
├── region/                  — определение региона
│   ├── extractor.py        — гибрид: regex + embeddings
│   ├── regex.py            — 26 паттернов
│   ├── embeddings.py       — семантический поиск
│   ├── db_client.py        — чтение noise_laws.db
│   └── data/
│       ├── noise_laws.db   — 85 законов
│       └── embeddings.json — 85 векторов
│
├── modules/                 — модули
│   ├── uk/                 — жалоба в УК
│   │   ├── hardchecks.py
│   │   ├── entity_check.py
│   │   ├── pre_checks.py
│   │   └── pdf.py
│   ├── noise/              — жалоба на шум
│   │   ├── hardchecks.py
│   │   ├── pre_checks.py
│   │   └── pdf.py
│   └── consumer/           — потребитель (в планах)
│
├── web/                     — Flask-приложение
│   ├── app.py
│   ├── schema.sql
│   ├── templates/
│   ├── static/
│   ├── requirements.txt
│   └── .env
│
├── scripts/                 — разовые утилиты
├── tests/                   — 12 файлов
├── docs/                    — документация
└── deploy/                  — инфраструктура

## Поток данных (модуль 2 — УК)

1. Пользователь заполняет форму
        ↓
2. Валидация полей:
   — телефон → core.phone_check
   — ФИО → core.name_declension
   — адрес (обязательно)
        ↓
3. Hard-check (modules.uk.hardchecks):
   — emergency → STOP
   — слишком коротко → STOP
   — нет букв → STOP
   — слишком общее → STOP
   — соседи → STOP
   — нет адреса → STOP
        ↓
4. LLM (Alice AI Flash):
   — нормализация текста
   — возвращает JSON с 3 нормами
        ↓
5. Entity check (modules.uk.entity_check):
   — проверяет сохранение существенных фактов
   — если потеряны → retry
        ↓
6. Pre-check (modules.uk.pre_checks):
   — объект проблемы определён? (уборка, лифт, крыша)
   — если нет → DOCUMENT BLOCKED
   — если да → идём дальше
        ↓
7. Legal Trace:
   — факт + квалификация + 3 нормы + источник
        ↓
8. PDF (modules.uk.pdf):
   — шапка, тело, 3 нормы, ПРОШУ, подпись
   — внизу подвал: движок, правила, шаблон
        ↓
9. CASE сохраняется в БД
        ↓
10. PDF отдаётся пользователю

## Поток данных (модуль 3 — Шум)

Отличия от модуля 2:

4.5. Определение региона:
   — region.extractor.extract_region(адрес)
   — regex → если не сработали, embeddings
   — region.db_client.get_law_for_region(регион)
        ↓
   Возвращает {"закон": "...", "url": "...", "version": "..."}
        ↓
8. PDF (modules.noise.pdf):
   — если закон найден → «нарушают требования: 1. Закон...»
   — если не найден → нейтральная формулировка

Pre-check для шума проверяет:
   — вид шума (музыка, ремонт, крики, лай собаки)
   — источник шума (сосед сверху, из кв. N, за стеной)
   — если нет → DOCUMENT BLOCKED

## Хранение данных

### Сейчас
- region/data/noise_laws.db — SQLite, 85 законов
- region/data/embeddings.json — 85 векторов (405 КБ)
- web/cases.db — SQLite, CASE + PDF + события
- /opt/legal_mind/logs/requests.log — метаданные запросов

### Планируется
- Миграция на Yandex Managed PostgreSQL (когда будет нагрузка)
- Object Storage для PDF (когда накопится много файлов)
- Key Management Service для секретов

## Внешние сервисы

Сервис                          | Назначение                | Endpoint
--------------------------------|---------------------------|---------
Alice AI Flash                  | Нормализация              | ai.api.cloud.yandex.net/v1
Yandex Text Embeddings          | Определение региона       | llm.api.cloud.yandex.net
Yandex Search API               | Сбор базы регионов (разово)| searchapi.api.cloud.yandex.net/v2
YandexGPT Pro                   | RAG (разово)              | llm.api.cloud.yandex.net

## Безопасность

- HTTPS через Let's Encrypt (после покупки домена)
- .env с правами 600, не в git
- Отдельный пользователь legal для gunicorn
- gunicorn слушает только на 127.0.0.1:5000
- Логи без персональных данных
- Deploy Key сервера — read-only на репозиторий
- SSH_PRIVATE_KEY для GitHub Actions — отдельный ключ

## Автодеплой

git push → GitHub Actions → SSH на VPS → git pull → restart → health check

Workflow (.github/workflows/deploy.yml):
1. Checkout — уже не нужен, работаем на сервере
2. SSH на 201.24.49.121
3. cd /opt/legal_mind
4. git fetch origin main
5. git reset --hard origin/main
6. chown -R legal:legal .
7. chmod 600 web/.env
8. systemctl restart legal-mind
9. curl http://127.0.0.1:5000/health
10. При провале — задача красная

## Что НЕ делаем архитектурно

- Не храним ПД без HTTPS
- Не отправляем документы от имени пользователя
- Не используем LLM для выбора законов
- Не вызываем LLM без hard-check
- Не генерируем PDF, если pre-check заблокировал