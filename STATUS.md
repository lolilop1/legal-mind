# Статус проекта Legal Mind

Дата: 13.09.2026

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
Git + .gitignore                       | OK
Модульная структура                    | OK
Тесты (15 файлов, 305 проверок)        | OK (305/305)
Adversarial (29 кейсов)                | OK (29/29)
Домен + HTTPS                          | ждёт оплаты
Модуль 1 (Потребитель, 4 сценария)     | OK
Обкатка мини-тестерами                 | идёт

## Что сделано

### Модульность
Переехали с плоской на модульную. 15 файлов тестов, 304 проверок. systemd + nginx обновлены.

### CASE (этап 3)
core/case_db.py, core/case_id.py, web/schema.sql. Экран /my, карточка /case. core/labels.py.

### Confidence / UNKNOWN (этап 4)
core/pre_checks.py + 2 модуля. Экран pre_check_blocked.html. Pre-check в DNA.

### Legal Trace (этап 5)
core/trace.py — цепочка Факт → Квалификация → Норма → Источник. Блок в карточке.

### Версионность (этап 6)
RULES_DATE, TEMPLATE_VERSION. PDF-подвал. Блок в карточке.

### Автодеплой (этап 8)
GitHub репо lolilop1/legal-mind. Deploy Key. workflow deploy.yml. git push → 30 сек.

### Security-патч (13.09.2026)
IDOR в /case/<ref>/pdf/<doc_id> — доступ к документу проверялся только
по case_ref, а сам doc_id (глобальный AUTOINCREMENT) не проверялся на
принадлежность делу. Теперь get_document_content(doc_id, case_number)
фильтрует по обеим. Заодно: create_case — атомарная генерация номера
(BEGIN IMMEDIATE + retry, раньше была гонка при параллельных запросах);
SECRET_KEY обязателен (без тихого insecure-дефолта); openai>=1.66
(нужен Responses API, 1.50 его не гарантирует).

### Security-патч (13.09.2026)
IDOR в /case/<ref>/pdf/<doc_id> — доступ к документу проверялся только
по case_ref, а сам doc_id (глобальный AUTOINCREMENT) не проверялся на
принадлежность делу. Теперь get_document_content(doc_id, case_number)
фильтрует по обеим. Заодно: create_case — атомарная генерация номера
(BEGIN IMMEDIATE + retry, раньше была гонка при параллельных запросах);
SECRET_KEY обязателен (без тихого insecure-дефолта); openai>=1.66
(нужен Responses API, 1.50 его не гарантирует).

### Модуль 1 (Потребитель)
4 сценария: defect, return14, marketplace, service. Авто-детект по тексту.
Умная шапка PDF (ООО/ИП/самозанятый/физлицо/ник). Физлица — адрес ИЛИ ссылка на профиль.
Нормализация телефона. Inline-валидация формы. Air Datepicker.

### Документация
README, STATUS, ROADMAP, docs/ARCHITECTURE, DECISIONS, MODULES, CHANGELOG, SETUP.

## Сигналы от тестеров

95% обращений — про потребителя.

## Известные ограничения

- CASE в session — потерял cookie = потерял список
- Нет HTTPS — ждёт домена
- CASE без шифрования

## История багов

Форма обнулялась при ошибке → session. Все ошибки по одной → список разом. «В квартире № 44» как источник шума → промпт. Потеряно «убивают жильцов» → маркеры. Адрес без запятых → core/address. Счётчик дел больше реального → index(). CSS не грузился → права. Нет топ-бара на стопе → шаблон. Import pre_checks не добавился → локальная правка. Leftover endif в case.html → перезапись. IDOR в /case/pdf — doc_id не проверялся на принадлежность делу → фильтр по case_number. Гонка case_number при параллельных запросах → BEGIN IMMEDIATE + retry.

## Что дальше

1. Домен + HTTPS
2. Обкатка мини-тестерами (УК + Шум + Потребитель)
3. Email-отправка PDF (этап 9)

## Ссылки

README.md, ROADMAP.md, docs/.