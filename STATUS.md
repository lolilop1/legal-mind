# Статус проекта Legal Mind

Дата: 2026-09-13

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
Тесты (23 файла, 644 проверки)         | OK (644/644)
UI-тесты (Playwright, 19)              | OK
Adversarial (29 кейсов)                | OK (29/29)
Домен + HTTPS                          | ждёт оплаты
Модуль 1 (Потребитель, 4 сценария)     | OK + расширения
Обкатка мини-тестерами                 | идёт

## Что сделано

### Модульность
Модульная структура (core/region/modules/web/scripts/tests/docs/deploy). 23 файла тестов, 644 проверки.

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
- .github/workflows/test.yml — 644 теста на каждый push
- .github/workflows/deploy.yml — через workflow_run только после Tests
- .github/workflows/smoke.yml — 6 сценариев против прода, понедельники 9:00 МСК + вручную
- Бейджи в README (Tests, Deploy, Smoke)

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
- Услуги: 4 подтипа (ст. 27-33) — срок / смета / отказ / некачество
- Калькулятор неустойки — ст. 22/23 (1%/день), ст. 23.1 (0.5%/день), ст. 28 (3%/день cap), ст. 20/23 (ремонт >45 дней, 1%/день)
- Отказ в гарантийном ремонте — подтип defect (ст. 18, 20, 21)
- Просрочка доставки — подтип marketplace (ст. 23.1)

### Безопасность (13.09.2026)
- IDOR в /case/<ref>/pdf/<doc_id> закрыт — фильтр по (id, case_number)
- Гонка case_number — BEGIN IMMEDIATE + retry
- SECRET_KEY обязателен (RuntimeError при отсутствии)
- Cookie flags: HttpOnly, SameSite=Lax, Secure-условно
- ProxyFix для правильного IP
- ПДн убраны из логов (только len=N)

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
2. Оставшиеся пункты Модуля 1: cap для ст. 23, срок гарантии vs срок годности, моральный вред
3. Этап 12: один CASE → много документов (претензия → иск → жалоба в РПН)
4. Email-отправка PDF (этап 9)

## Ссылки

README.md, ROADMAP.md, docs/.