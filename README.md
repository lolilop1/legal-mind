# Legal Mind

Веб-сервис для физических лиц. Превращает неформальное описание бытовой проблемы в готовый юридический документ (PDF).

**Работает:** http://201.24.49.121/
**Домен:** legalmind.su (ждёт оплаты)

## Что работает

### Модуль 2 — Жалоба в УК

Уборка подъезда, отопление, лифт, снег, крыша, домофон.

Нормы (федеральные): статья 161 ЖК РФ, Постановление № 491, Постановление № 170.

### Модуль 3 — Жалоба на шум

Музыка, ремонт, крики, лай собаки, топот, вечеринки.

Нормы: региональные (85 субъектов в region/data/noise_laws.db). Регион определяется гибридно: regex (26 паттернов) + embeddings (fallback).

### CASE-хранилище

Каждое заявление сохраняется в SQLite. Номер: LM-YYYYMMDD-NNNN, доступ по паре номер+UUID. Экран /my — список дел, /case/... — карточка.

## Архитектура

Пользователь → nginx → Flask → валидация → hard-check → Alice AI Flash → entity check → PDF → CASE.

Принцип: если что-то можно проверить кодом — проверяем кодом.

## Стек

Python 3.14, Flask, gunicorn, nginx, systemd, fpdf2, pymorphy3, Alice AI Flash, Yandex Text Embeddings, SQLite. Хостинг: Timeweb Cloud, IP 201.24.49.121.

## Структура

- core/ — общий код
- region/ — определение региона
- modules/ — uk, noise, consumer
- web/ — Flask
- scripts/ — разовые утилиты
- tests/ — 10 файлов, 196 проверок
- docs/ — документация
- deploy/ — инфраструктура

## Быстрый старт

Полная инструкция — docs/SETUP.md.

Установка: pip install -r web/requirements.txt, заполнить web/.env, запустить python web/app.py.

## Деплой

.\deploy\deploy.ps1

## Управление на сервере

ssh root@201.24.49.121, systemctl status legal-mind.

## Roadmap

См. ROADMAP.md. Ближайшее: домен legalmind.su + HTTPS, Модуль 1 (Потребитель), обкатка.

## Ссылки

STATUS.md, ROADMAP.md, docs/DECISIONS.md, docs/ARCHITECTURE.md, docs/MODULES.md, docs/SETUP.md, docs/CHANGELOG.md.