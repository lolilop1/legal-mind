# Health-check: мониторинг Legal Mind

Cloud Function в Yandex Cloud. Дёргает /health каждые 5 минут,
при падении шлёт в Telegram.

## Файлы
- index.py — код функции
- requirements.txt — boto3, requests

## Переменные окружения

- HEALTH_URL — URL /health (default: http://201.24.49.121/health)
- TELEGRAM_BOT_TOKEN — токен от @BotFather
- TELEGRAM_CHAT_ID — ID чата
- YC_S3_KEY_ID, YC_S3_SECRET — статический ключ сервисного аккаунта
- YC_S3_BUCKET — default: legal-mind-backups
- YC_S3_STATE_KEY — default: monitoring/state.json

## Настройка

1. Telegram-бот: @BotFather -> /newbot -> токен
2. Узнать chat_id: https://api.telegram.org/bot<TOKEN>/getUpdates
3. Console -> Cloud Functions -> Создать функцию
4. Среда: Python 3.12, точка входа: index.handler
5. Загрузить index.py + requirements.txt
6. Память 128 МБ, таймаут 15 сек
7. Прописать env-переменные
8. Триггер: Таймер, cron: */5 * * * ? *
9. Тест: входные данные {} -> должно вернуть statusCode 200

## Проверка алертов

SSH на сервер:
- systemctl stop legal-mind  -> через 5 мин в Telegram приходит 🔴
- systemctl start legal-mind -> через 5 мин приходит 🟢

## Логи

Console -> Cloud Functions -> функция -> Логи
Или: yc serverless function logs legal-mind-health-check
