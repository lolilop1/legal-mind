# Legal Mind — Web

Веб-приложение: HTML-форма → PDF-заявление.
Развёрнуто на VPS: **http://201.24.49.121/**

## Как пользоваться

1. Открой в браузере **http://201.24.49.121/**
2. Выбери тип проблемы (УК / Шум).
3. Заполни поля.
4. Нажми «Составить заявление» — скачается PDF.
5. Если форма вернёт стоп-сообщение — исправь данные и попробуй снова.

## Что внутри

- `app.py` — Flask-приложение.
- `templates/` — HTML-шаблоны.
- `static/` — CSS.
- `legal_mind_module2_*.py` — логика жалобы в УК.
- `legal_mind_module3_*.py` — логика жалобы на шум.
- `.env` — API-ключи (не в git!).
- `requirements.txt` — зависимости Python.

## Сервер

- Провайдер: Timeweb Cloud
- IP: **201.24.49.121**
- ОС: Ubuntu 22.04 / 24.04
- Процесс-менеджер: systemd (`legal-mind.service`)
- Веб-сервер: nginx (reverse proxy на 127.0.0.1:5000)
- Application server: gunicorn (2 воркера)

## Развёртывание

См. `deploy.md` — полная инструкция с нуля.

## Обновление кода

С локальной машины:

```powershell
cd C:\Users\Ilay\Desktop\LegalMind\с_дипсик\в1
scp -r * root@201.24.49.121:/opt/legal_mind/
```

На сервере:

```bash
chown -R legal:legal /opt/legal_mind
systemctl restart legal-mind
```

## Перезапуск / статус

```bash
systemctl status legal-mind
systemctl restart legal-mind
systemctl stop legal-mind
journalctl -u legal-mind -f     # живой хвост логов
```

## Переменные окружения (`.env`)

```
YANDEX_API_KEY   — API-ключ Yandex Cloud
YANDEX_FOLDER_ID — folder ID Yandex Cloud
```

Ключ получается в Yandex Cloud: сервисный аккаунт → роль `ai.languageModels.user`
→ API-ключ.

## Проверка доступности

Из браузера: `http://201.24.49.121/`
Из консоли сервера: `curl http://127.0.0.1:5000/health`

Ожидаемый ответ:
```json
{"status": "ok", "llm_configured": true}
```

## Что дальше

- Собрать реальные кейсы от 5–10 знакомых через форму.
- По результатам — доработки.
- Опционально: домен вместо IP, HTTPS через Let's Encrypt.