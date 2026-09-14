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
        |— Калькулятор неустойки (для consumer)
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
    │   └── consumer/           — потребитель
    │       ├── engine.py
    │       ├── pdf.py
    │       ├── hardchecks.py
    │       ├── pre_checks.py       — подтипы (услуга/marketplace/defect)
    │       ├── scenario_detect.py  — авто-детект сценария
    │       ├── marketplaces.py     — справочник 12 площадок
    │       ├── calculators.py      — неустойка (6 ставок)
    │       ├── seller_kind.py      — тип продавца (юрлицо/физлицо)
    │       ├── demands.py          — 9 требований юзера (срок + статья)
    │       ├── entity_check.py     — anti-hallucination (числа + даты)
    │       └── configs/
    │           ├── defect.py       — ст. 18, 20, 21, 23 (отказ в ремонте)
    │           ├── return14.py     — ст. 25 + невозвратные/техсложные
    │           ├── marketplace.py  — ст. 26.1, 23.1 (доставка)
    │           └── service.py      — ст. 27-33 + 5 спец.видов
    │
    ├── web/                     — Flask-приложение
    │   ├── app.py
    │   ├── schema.sql
    │   ├── templates/
    │   ├── static/
    │   ├── requirements.txt
    │   └── .env
    │
    ├── scripts/                 — утилиты + smoke
    ├── tests/                   — 32 файла, 2298 проверок
    ├── docs/                    — документация
    ├── deploy/                  — инфраструктура
    └── .github/workflows/       — CI/CD

## Поток данных (модуль 2 — УК)

1. Пользователь заполняет форму
2. Валидация полей (телефон, ФИО, адрес)
3. Hard-check (emergency, короткое, нет букв, соседи, нет адреса)
4. LLM (Alice AI Flash): нормализация, 3 нормы
5. Entity check: сохранены ли факты (дети, инвалиды, кв.)
6. Pre-check: объект проблемы определён?
7. Legal Trace: факт + квалификация + 3 нормы + источник
8. PDF (fpdf2): шапка, тело, нормы, ПРОШУ, версия в подвале
9. CASE сохраняется в БД
10. PDF отдаётся пользователю

## Поток данных (модуль 3 — Шум)

Отличия от модуля 2:
- Определение региона (regex → embeddings) + чтение закона из БД
- PDF: «нарушают требования: 1. Закон ...» или нейтральная формулировка
- Pre-check: вид шума + источник шума (критично)

## Поток данных (модуль 1 — Потребитель)

1. Пользователь заполняет wizard (3 шага)
2. Scenario detect (regex): defect / return14 / marketplace / service
3. Hard-check (общий + специфика сценария):
   - невозвратные (2463) для return14 → STOP
   - техсложные (924) для return14 → STOP
   - маркетплейс без номера заказа → STOP
   - адрес продавца для ООО/ИП → STOP
4. Юзер выбирает требование (money/replace/repair/…)
   → `/detect_category` отдаёт список под сценарий
   → UI рендерит radio-карточки в секции «Что требуете»
5. LLM (Alice AI Flash) с конфигом сценария + выбранным требованием
6. Валидация норм по whitelist
7. Anti-hallucination — `check_consumer_numeric_recall`:
   все даты и цены в формальном тексте должны быть во входе.
   Ретрай → вырезание выживших галлюцинаций
8. Жёсткая подмена `parsed["требование"]` выбранным кодом
9. Pre-check (known / critical / optional):
   - Подтип услуги (срок/смета/отказ/некачество + банк/страх/туризм/образование/медицина)
   - Подтип marketplace (доставка/недостоверная/брак)
   - Подтип defect (отказ в ремонте / просрочка 45 дней / стандарт)
   - Ст. 10 (право на информацию), ст. 12 (недостоверная)
   - Ст. 16 (ничтожные условия), ст. 19 (гарантия vs 2 года)
   - Оговорка 15 дней, номер заказа для marketplace
10. Калькулятор неустойки (по сценарию + подтипу):
    - defect/return14/marketplace 1%, service 3% (cap)
    - delivery_delay 0.5% (cap = предоплата), repair_delay 1% (45 дн.)
    - Ст. 24: если цена поднялась — расчёт по текущей
11. PDF: шапка (умный адресат) + тело + нормы + ТРЕБУЮ (п. 4 — ст. 15)
        + РАСЧЁТ НЕУСТОЙКИ + подвал. Срок и wording требования —
        из формы (`требование_выбор`), не от LLM
12. CASE сохраняется в БД (+ calculation JSON для карточки)
13. Redirect в карточку + авто-скачивание PDF

## Хранение данных

### Сейчас
- `region/data/noise_laws.db` — SQLite, 85 законов
- `region/data/embeddings.json` — 85 векторов (405 КБ)
- `web/cases.db` — SQLite (WAL), CASE + PDF + события + calculation (JSON)
- `/opt/legal_mind/logs/requests.log` — метаданные запросов (без ПДн)
- `s3://legal-mind-backups/daily/` — ежедневные бэкапы cases.db,
  **зашифрованы** `aes-256-cbc -pbkdf2 -iter 100000`, пароль в
  Yandex Lockbox (retention 30 дней, cron 03:00 UTC)

### Планируется
- Миграция на Yandex Managed PostgreSQL (когда будет нагрузка)
- Object Storage для PDF (когда накопится много)
- Key Management Service для секретов

## Внешние сервисы

Сервис                          | Назначение
--------------------------------|-------------------------------------
Alice AI Flash                  | Нормализация текста
Yandex Text Embeddings          | Определение региона
Yandex Search API               | Сбор базы регионов (разово)
YandexGPT Pro                   | RAG (разово)

## Безопасность

Пройден внешний аудит (13-14.09.2026), закрыто 10 из 11.

- HTTPS через Let's Encrypt (после домена)
- .env + .env.backup — права 600, не в git
- Отдельный пользователь `legal` для gunicorn
- gunicorn слушает только на 127.0.0.1:5000
- Логи без ПДн
- Deploy Key — read-only
- SECRET_KEY обязателен
- Cookie: HttpOnly, SameSite=Lax, Secure (при HTTPS)
- IDOR закрыт в `/case/<ref>/pdf/<id>` (фильтр по case_number)
- **CSRF** — токен в session + hmac.compare_digest
- **Rate limiting** — nginx `limit_req` + Python in-memory (50/сутки)
- **152-ФЗ** — чекбокс согласия + /privacy + серверная проверка
- **Бэкапы cases.db** — ежедневно в Yandex Object Storage (cron),
  **зашифрованы** aes-256-cbc, пароль из Yandex Lockbox
- **WAL для SQLite** — `PRAGMA journal_mode=WAL`, `synchronous=NORMAL`
- **Lockbox** — `core/lockbox.py`, REST API
  (`payload.lockbox.api.cloud.yandex.net`), IAM-токен кэш 11 ч
- **Обёртка `scripts/run_backup.sh`** для cron (защита от гонки с деплоем)

## CI/CD

### test.yml
Push → GitHub Actions → 2298 тестов на Python 3.12 + chromium (Playwright).
Actions: `checkout@v5`, `setup-python@v6`, `upload-artifact@v5`.
Если красное — деплой не запустится.

### deploy.yml
Триггерится через `workflow_run` после успешного `test.yml`.
Также `workflow_dispatch` для ручного обхода.

Шаги:
1. SSH на 201.24.49.121
2. cd /opt/legal_mind
3. git fetch && git reset --hard origin/main
4. chown/chmod
5. systemctl restart legal-mind
6. curl /health — проверка
7. При провале — красный

### Мониторинг
Cloud Function в Yandex Cloud (`deploy/health_check/`) — Timer Trigger
каждые 5 минут дёргает `/health`. При смене статуса (ok→fail / fail→ok)
шлёт в Telegram. Состояние — в `s3://legal-mind-backups/monitoring/state.json`
(антифлуд). Подробнее: `deploy/health_check/README.md`.

### smoke.yml
- По понедельникам 9:00 МСК (`cron: '0 6 * * 1'`)
- Ручной запуск: Actions → Smoke Test → Run workflow
- 6 сценариев против прода, артефакты (6 PDF) сохраняются 30 дней
- Email при падении

## UI-структура

- **Главная `/`** — hero + 3 карточки выбора типа проблемы
  (радио-кнопки внутри `.type-card` label) + wizard 3 шага
- **Шаг 1** — выбор типа (карточки) + textarea «Опишите проблему»
- **Шаг 2** — 4 секции `.form-section`:
  📍 Ваш адрес / 🏢 Продавец / 🛍️ Товар / 📅 Дата обращения
- **Шаг 3** — ФИО + телефон + чекбокс 152-ФЗ
- **Карточка дела `/case/...`** — знаем / расчёт / версия /
  документы / исходное описание
- **Скриншоты** — `scripts/make_screenshots.py` (7 PNG,
  desktop + mobile, Playwright headless)

Статика:
- `style.css` — `.hero`, `.type-card`, `.form-section`, `.lm-field-error`,
  `.privacy-consent`, кастомная тема Air Datepicker
- Air Datepicker — 2 календаря через `initPicker()` (общий locale)

## Что НЕ делаем архитектурно

- Не храним ПД без HTTPS
- Не отправляем документы от имени пользователя
- Не используем LLM для выбора законов
- Не вызываем LLM без hard-check
- Не генерируем PDF, если pre-check заблокировал
- Не позволяем LLM выдумывать числа и даты (entity_check)
- Не позволяем LLM выбирать требование за юзера (demands.py)
- Не пропускаем криминальные запросы (криминал-фильтр)