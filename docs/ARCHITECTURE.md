# Legal Mind — Architecture

## Высокоуровневая схема

```text
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
        |— [Модуль 3]: определение региона + чтение закона
        |— PDF: fpdf2
        |
        v
PDF-документ (в памяти → send_file → скачивание)
```

## Структура папок

```text
legal_mind/
├── core/                    — общий код
│   ├── llm.py              — клиент Alice AI Flash
│   ├── name_declension.py  — склонение ФИО (pymorphy3)
│   └── phone_check.py      — валидация телефона
│
├── region/                  — определение региона
│   ├── extractor.py        — гибрид: regex + embeddings
│   ├── regex.py            — 26 паттернов на 85 регионов
│   ├── embeddings.py       — семантический поиск
│   ├── db_client.py        — чтение noise_laws.db
│   └── data/
│       ├── noise_laws.db   — 85 законов
│       └── embeddings.json — 85 векторов
│
├── modules/                 — модули (по одному на категорию)
│   ├── uk/                 — жалоба в УК
│   │   ├── hardchecks.py
│   │   ├── entity_check.py
│   │   └── pdf.py
│   ├── noise/              — жалоба на шум
│   │   ├── hardchecks.py
│   │   └── pdf.py
│   └── consumer/           — потребитель (в разработке)
│
├── web/                     — Flask-приложение
│   ├── app.py              — роуты, оркестрация
│   ├── templates/          — HTML
│   ├── static/             — CSS
│   ├── requirements.txt
│   └── .env                — ключи (НЕ в git)
│
├── scripts/                 — разовые утилиты (НЕ на сервер)
│   ├── build_embeddings.py — сборка эмбеддингов
│   ├── rag_mass_v4.py      — сборка базы регионов
│   ├── rag_hardcode_fixed.py
│   ├── batch_pdf_from_results.py
│   └── adversarial_tests.py
│
├── tests/                   — тесты (НЕ на сервер)
│   ├── _bootstrap.py       — настройка sys.path
│   ├── run_all.py          — запуск всех
│   └── test_*.py
│
├── docs/                    — документация
│   ├── DECISIONS.md
│   ├── CHANGELOG.md
│   ├── ARCHITECTURE.md     — этот файл
│   └── MODULES.md
│
└── deploy/                  — инфраструктура
    ├── legal-mind.service  — systemd unit
    ├── nginx.conf          — reverse proxy
    ├── deploy.ps1          — умный деплой
    └── deploy.md
```

## Поток данных (модуль 2 — УК)

```text
1. Пользователь заполняет форму
        ↓
2. Валидация полей:
   — телефон → core.phone_check
   — ФИО → core.name_declension
   — адрес (обязательно)
        ↓
3. Hard-check (modules.uk.hardchecks):
   — экстренность (газ, пожар) → STOP
   — слишком коротко → STOP
   — нет букв → STOP
   — слишком общее → STOP
   — соседи → STOP (не тот модуль)
   — нет адреса → STOP
        ↓
4. LLM (Alice AI Flash):
   — нормализация текста
   — возвращает JSON с 3 нормами
        ↓
5. Entity check (modules.uk.entity_check):
   — проверяет, что все существенные факты сохранены
   — если потеряны → retry с явным указанием
        ↓
6. PDF (modules.uk.pdf):
   — шапка, тело, 3 нормы, ПРОШУ, дата, подпись
        ↓
7. Ответ пользователю (send_file)
```

## Поток данных (модуль 3 — Шум)

Отличие — **шаг 4.5**:

```text
4.5. Определение региона:
   — region.extractor.extract_region(адрес)
   — regex → если не сработали, embeddings
   — region.db_client.get_law_for_region(регион)
        ↓
   Возвращает {"закон": "...", "url": "...", "version": "..."}
        ↓
6. PDF (modules.noise.pdf):
   — если закон найден → «нарушают требования: 1. Закон...»
   — если не найден → нейтральная формулировка
```

## Хранение данных

### Сейчас
- `region/data/noise_laws.db` — SQLite, 85 законов
- `region/data/embeddings.json` — 85 векторов (405 КБ)
- `/opt/legal_mind/logs/requests.log` — метаданные запросов (без ПД)
- **CASE не хранится** — PDF генерируется в памяти и отдаётся

### Планируется (этап 3)
- `web/cases.db` — SQLite, CASE DNA + PDF + файлы
- UUID + номер CASE для доступа
- Позже: миграция на Yandex Managed PostgreSQL

## Внешние сервисы

| Сервис | Назначение | Endpoint |
|---|---|---|
| Alice AI Flash | Нормализация | `ai.api.cloud.yandex.net/v1` |
| Yandex Text Embeddings | Определение региона | `llm.api.cloud.yandex.net` |
| Yandex Search API | Сбор базы регионов (разово) | `searchapi.api.cloud.yandex.net/v2` |
| YandexGPT Pro | RAG (разово) | `llm.api.cloud.yandex.net` |

## Безопасность

- HTTPS через Let's Encrypt (после покупки домена)
- `.env` с правами 600, не в git
- Отдельный пользователь `legal` для gunicorn
- gunicorn слушает только на `127.0.0.1:5000` (закрыт снаружи)
- Логи без персональных данных

## Что НЕ делаем архитектурно

- Не храним ПД без HTTPS
- Не отправляем документы от имени пользователя
- Не используем LLM для выбора законов
- Не вызываем LLM без hard-check (сначала код, потом модель)