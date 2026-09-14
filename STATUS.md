# Статус проекта Legal Mind

Дата: 2026-09-14 (вечер)

## Краткая сводка

Компонент                              | Статус
---------------------------------------|--------
Модуль 2 (УК)                          | OK
Модуль 3 (шум, 85 регионов)            | OK
Гибридное определение региона          | OK (26/26)
CASE-хранилище                         | OK
Экраны /my и /case                     | OK
Confidence / UNKNOWN (этап 4)          | OK
Legal Trace (этап 5)                   | OK
Версионность (этап 6)                  | OK
Автодеплой (этап 8)                    | OK
CI: Tests + Deploy + Smoke             | OK
Модульная структура                    | OK
Тесты (32 файла, 2298 проверок)             | OK (2298/2298)
UI-тесты (Playwright, 19)              | OK
Adversarial (29 кейсов)                | OK (29/29)
Домен + HTTPS                          | ждёт оплаты
Модуль 1 (Потребитель, 4 сценария)     | OK + расширения
Обкатка мини-тестерами                 | идёт

## Что сделано

### Модульность
Модульная структура (core/region/modules/web/scripts/tests/docs/deploy). 32 файла тестов, 2298 проверок.

### CASE (этап 3)
core/case_db.py, core/case_id.py, web/schema.sql. Экран /my, карточка /case. core/labels.py.

### Confidence / UNKNOWN (этап 4)
core/pre_checks.py + pre-checks для UK / noise / consumer. Экран pre_check_blocked.html. Pre-check идёт в DNA.

### Legal Trace (этап 5)
core/trace.py — цепочка Факт → Квалификация → Норма → Источник. Блок в карточке дела.

### Версионность (этап 6)
RULES_DATE, TEMPLATE_VERSION. PDF-подвал. Блок в карточке.

### Автодеплой (этап 8)
GitHub репо lolilop1/legal-mind. Deploy Key. deploy.yml через workflow_run — срабатывает ТОЛЬКО после зелёных Tests. Ручной deploy.ps1 остался как fallback.

### CI/CD (13.09.2026)
- .github/workflows/test.yml — 2177 тестов на каждый push
- .github/workflows/deploy.yml — через workflow_run только после Tests
- .github/workflows/smoke.yml — 6 сценариев против прода, понедельники 9:00 МСК + вручную
- Бейджи в README (Tests, Deploy, Smoke)

### Модуль 1 (Потребитель) — 84 категории (14.09.2026)

- 84 категории в `modules/consumer/categories.py`
- `detect_category()` — авто-детект (59 тестов)
- PDF: «о возврате стоимости смартфона» вместо «товара»
- UI-плашка «Определилось: смартфона — возврат/по браку»
- Endpoint `/detect_category`
- `tech_complex` — Пост. 924

### Модуль 2 (УК) — 181 тип документа (14.09.2026)

- 181 конфиг в `modules/uk/configs/`
- Общий `engine.py` (importlib вместо if-ов)
- PDF параметризован (`pdf_title`, `pdf_subtitle`, `pdf_request_block`)
- **Авто-детект типа** — `doc_detect.py`, 45 тестов
- `app.py` — `auto_detect=1` в форме (без флага default `uk`)
- Тесты: `test_uk_engine` (114), `test_uk_pdf_types` (sample 20),
  `test_uk_configs_all` (724), `test_uk_doc_detect` (45)
- Полный прогон: 40 сек (было 58 — sample PDF вместо 181)

### Модуль 1 (Потребитель) — 4 сценария + расширения

**Базовые сценарии:**
- defect (ст. 18) — товар с браком
- return14 (ст. 25) — не подошёл за 14 дней
- marketplace (ст. 26.1) — Ozon, WB, Яндекс Маркет, Avito и др.
- service (ст. 29) — ремонт, курсы, юруслуги, доставка

**Расширения (сессия 13.09.2026):**
- Невозвратные товары (Пост. 2463) — стоп для return14
- Техсложные товары (Пост. 924) — стоп для return14
- Оговорка 15 дней ст. 18 — warning в pre-check для defect
- Справочник 12 маркетплейсов (реестр МЭР) — modules/consumer/marketplaces.py
- Номер заказа + автоадрес владельца агрегатора для маркетплейсов
- Услуги: 4 базовых подтипа + 5 новых спец (банк/страховка/туризм/образование/медицина)
- Калькулятор неустойки — ст. 22/23 (1%/день), ст. 23.1 (0.5%/день), ст. 28 (3%/день cap), ст. 20/23 (ремонт >45 дней, 1%/день)
- Отказ в гарантийном ремонте — подтип defect (ст. 18, 20, 21)
- Просрочка доставки — подтип marketplace (ст. 23.1)
- Срок гарантии vs 2 года — ст. 19 ЗоЗПП
- Ничтожные условия продавца — ст. 16 ЗоЗПП
- Компенсация морального вреда — ст. 15 ЗоЗПП (пункт 4 в требовании)
- Расчёт по текущей цене товара — ст. 24 ЗоЗПП
- Право на информацию — ст. 10 ЗоЗПП
- Недостоверная информация — ст. 12 ЗоЗПП
- Расчёт неустойки в PDF **и** в карточке дела (блок «Расчёт неустойки»)
- Авто-детект подтипов через pre-checks (llm выбирает нормы по фактам)

### Фиксы consumer по итогам ред-тима (14.09.2026, вечер)

Тестер-ред-тимер нашёл 6 багов. Все закрыты + бонус.

**Критичные:**
- **Криминал-фильтр** — «сдать краденый товар по гарантии» → STOP.
  Жертву («мне продали краденое») не трогает. `hardchecks.py`
- **Срок 45→10 дней** — LLM возвращала «возврат денег» со сроком
  «ремонта» (ст. 20). Теперь `_match_demand_option` матчит по
  якорным корням. Возврат = 10 дн (ст. 22). `pdf.py`
- **Анти-галлюцинации** — LLM выдумывала дату покупки и цену.
  Новый `modules/consumer/entity_check.py`: числа и даты в
  формальном тексте должны быть во входе. Ретрай + вырезание.
- **«Продукты» для магнитофона** — regex `еды` ловил
  «сл**еды**». Добавили `` + `ед[аыу]`. `pre_checks.py`

**Смежные:**
- `_CONSUMER_MARKERS` — не ловил форму «вернуть»
- UI: убрали предзаполнение «Дата покупки» сегодняшним числом
- pre-check: аудиотехника (магнитофон, плеер) + fallback по подтипу
- pre-check: маркетплейс без адреса → не блокирует (Avito)
- `scenario_detect`: приоритет defect над return14 при явной поломке

### Фича: выбор требования (14.09.2026, вечер)

Юзер сам выбирает требование к продавцу — претензия не должна
содержать «либо вернуть, либо заменить, либо отремонтировать».

- `modules/consumer/demands.py` — 9 требований с кодами
  (money/replace/exchange/repair/discount/penalty/refuse/fix_free/delivery_refund)
- UI: секция «Что требуете» на шаге 2 — карточки с radio
- `/detect_category` отдаёт список требований для сценария
- `/submit` принимает `требование_код`, валидирует
- `engine.py` — жёстко подменяет требование от LLM выбранным
- `pdf.py` — берёт `требование_выбор` из формы (срок + wording)

Тесты: `test_consumer_demands.py` (71 проверка).

### Безопасность (13.09.2026)
- IDOR в /case/<ref>/pdf/<doc_id> закрыт — фильтр по (id, case_number)
- Гонка case_number — BEGIN IMMEDIATE + retry
- SECRET_KEY обязателен (RuntimeError при отсутствии)
- Cookie flags: HttpOnly, SameSite=Lax, Secure-условно
- ProxyFix для правильного IP
- ПДн убраны из логов (только len=N)
- **WAL для SQLite** — `PRAGMA journal_mode=WAL`, `synchronous=NORMAL`
- **Шифрование бэкапов** — `aes-256-cbc -pbkdf2 -iter 100000`, пароль из Lockbox
- **Yandex Lockbox** — `core/lockbox.py`, REST API, IAM-токен кэш 11 ч

### Security-аудит (13-14.09.2026)
Внешний аудит — закрыто 10 из 11 пунктов.

- **CSRF** — токен в session (hmac.compare_digest), скрытое поле
  `_csrf_token` в форме, 400 при провале. +5 тестов.
- **Rate limiting** — двойной слой: nginx `limit_req` (1 r/m на
  `/submit`) + Python in-memory (50 дел/сутки на IP). +5 тестов.
- **152-ФЗ** — чекбокс согласия + страница `/privacy` +
  серверная проверка. +6 тестов.
- **Бэкапы** — `cases.db` в Yandex Object Storage, **зашифрованы
  aes-256-cbc**, пароль из **Yandex Lockbox**, cron 03:00 UTC,
  retention 30 дней. `scripts/backup_db.py`. `docs/BACKUP.md`.
- **Дедуп** `_is_legal_entity` → `modules/consumer/seller_kind.py`
  (единая точка правды для Python). +37 тестов.
- **CI** — deploy только после зелёных тестов (`workflow_run`).
  Интеграционные тесты Flask-роутов через `test_client` (30 проверок).
- **Actions** обновлены: checkout@v5, setup-python@v6,
  upload-artifact@v5 (Node.js 20 → 24).

Осталось: шифрование `cases.db` at rest (отдельная сессия),
HTTPS (ждёт домена).

### UI (14.09.2026)
- Hero-секция с градиентом, 3 галочки преимуществ
- 3 карточки выбора типа проблемы (🏠 🔊 🛒) вместо dropdown
- Шаг 2 формы разбит на 4 секции (адрес / продавец / товар / дата)
- Цена + текущая цена — в 2 колонки
- Air Datepicker пофикшен (не вылетает за карточку)
- Playwright UI-тесты (22 проверки), 7 скриншотов через
  `scripts/make_screenshots.py`
- `.lm-field-error`, `.type-card`, `.form-section` в style.css

### Мониторинг (14.09.2026)
- Cloud Function в Yandex Cloud — дёргает `/health` каждые 5 мин
- Telegram-алерты при падении/восстановлении
- Антифлуд через S3 (`monitoring/state.json`)
- Timer Trigger `*/5 * * * ? *`
- Инструкция: `deploy/health_check/README.md`

### Документация
README, STATUS, ROADMAP, docs/ARCHITECTURE, DECISIONS, MODULES, CHANGELOG, SETUP, web/README — все синхронизированы с кодом.

## Сигналы от тестеров

95% обращений — про потребителя.

## Известные ограничения

- CASE в session — потерял cookie = потерял список
- Нет HTTPS — ждёт домена
- CASE без шифрования
- Email-отправка PDF (этап 9) — предусловие: домен + Postbox

## Что дальше

1. Домен + HTTPS (этап 1)
2. Оставшиеся пункты Модуля 1: инверсия смысла (LLM «есть»→«отсутствуют»), cap ст. 23
3. Этап 12: один CASE → много документов (претензия → иск → жалоба в РПН)
4. Email-отправка PDF (этап 9)

## Ссылки

README.md, ROADMAP.md, docs/.