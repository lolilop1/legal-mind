# Legal Mind — Web

Веб-приложение: HTML-форма → PDF-документ.
Прод: http://201.24.49.121/

## Как пользоваться

1. Открой http://201.24.49.121/
2. Выбери тип проблемы:
   - Жалоба в УК — уборка, отопление, лифт, крыша, домофон
   - Нарушение тишины — музыка, ремонт, крики, лай собаки
   - Защита прав потребителя — товар, услуга, маркетплейс
3. Заполни поля (форма пошаговая — 3 шага)
4. Нажми «Составить заявление» — PDF скачается автоматически, откроется карточка дела
5. Если форма вернёт стоп-сообщение — исправь данные и попробуй снова

## Что внутри

- app.py — Flask-приложение (роуты, process_uk / process_noise / process_consumer)
- templates/ — HTML-шаблоны (index, my, case, stop, pre_check_blocked)
- static/ — CSS + Air Datepicker
- .env — API-ключи (не в git!)
- requirements.txt — зависимости Python
- schema.sql — схема БД CASE

Логика модулей — в modules/ (на уровень выше):

- modules/uk/ — жалоба в УК
- modules/noise/ — жалоба на шум
- modules/consumer/ — защита прав потребителя (engine, configs, marketplaces, calculators, seller_kind)
- core/ — общий код (llm, case_db, name_declension, trace, pre_checks)
- region/ — определение региона (для шума)

## Сервер

- Провайдер: Timeweb Cloud
- IP: 201.24.49.121
- ОС: Ubuntu 22.04 / 24.04
- Процесс-менеджер: systemd (legal-mind.service)
- Веб-сервер: nginx (reverse proxy на 127.0.0.1:5000)
- Application server: gunicorn (2 воркера)

## Развёртывание

Полная инструкция — docs/SETUP.md (корень репо).

## Обновление кода

Автодеплой через git push:

    git push origin main

GitHub Actions → SSH на сервер → git pull → restart → health check (30 сек).

Резервный ручной деплой (если Actions недоступен):

    .\deploy\deploy.ps1

## Перезапуск / статус

    systemctl status legal-mind
    systemctl restart legal-mind
    journalctl -u legal-mind -f

## Переменные окружения (.env)

    YANDEX_API_KEY   — API-ключ Yandex Cloud
    YANDEX_FOLDER_ID — folder ID Yandex Cloud
    SECRET_KEY       — Flask session

Ключ получается в Yandex Cloud: сервисный аккаунт → роль ai.languageModels.user → API-ключ.

## Проверка доступности

Из браузера: http://201.24.49.121/
Из консоли сервера: curl http://127.0.0.1:5000/health

Ожидаемый ответ:

    {"status": "ok", "llm_configured": true, "cases_total": 0}

## UI

- **Hero-секция** на главной — крупный заголовок + 3 преимущества
- **3 карточки выбора типа проблемы** (🏠 УК / 🔊 Тишина / 🛒 Потребитель)
- **Wizard 3 шага**: Проблема → Детали → Контакты
- **Шаг 2** — 4 секции: адрес / продавец / товар / дата обращения
- **Air Datepicker** — 2 календаря (дата покупки + дата обращения)
- **Скриншоты** — `python scripts/make_screenshots.py` (7 PNG)

## Безопасность

- **CSRF** — токен в session, скрытое поле `_csrf_token` в форме
- **Rate limiting** — nginx 1 r/m на /submit + Python 50 дел/сутки на IP
- **152-ФЗ** — обязательный чекбокс согласия, страница /privacy
- **Cookie** — HttpOnly, SameSite=Lax, Secure (условно)
- **Логи без ПДн** — длина адреса, не сам адрес
- **Бэкапы** — cases.db в Object Storage, cron 03:00 UTC

## Что дальше

- Собрать реальные кейсы от 5-10 знакомых по всем 3 модулям
- По результатам — доработки
- Домен legalmind.su + HTTPS через Let's Encrypt
