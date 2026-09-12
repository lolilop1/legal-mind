# Деплой Legal Mind на Timeweb Cloud VPS

Сервер: **201.24.49.121**
ОС: Ubuntu 22.04 или 24.04, минимум 1 ГБ RAM.
Доступ: root по SSH.

## 1. Подключение

С локальной машины (PowerShell):

```powershell
ssh root@201.24.49.121
```

Пароль — из панели Timeweb. При первом подключении подтверди fingerprint (`yes`).

## 2. Установка системы

```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv nginx git fonts-dejavu
```

`fonts-dejavu` нужен для PDF — без него fpdf2 не найдёт шрифт с кириллицей.

## 3. Пользователь и папка

```bash
useradd -m -s /bin/bash legal
mkdir -p /opt/legal_mind
chown legal:legal /opt/legal_mind
```

## 4. Клонирование через git

На сервере (в SSH-сессии):

    git clone git@github.com:lolilop1/legal-mind.git /opt/legal_mind
    cd /opt/legal_mind

Если Deploy Key ещё не настроен — см. раздел «Автодеплой».

В /opt/legal_mind/ должно быть:
- core/, region/, modules/, web/, deploy/
- web/.env — создаётся вручную (в git его нет)
- web/requirements.txt

## 5. Права

```bash
chown -R legal:legal /opt/legal_mind
chmod 600 /opt/legal_mind/.env
```

## 6. Виртуальное окружение

```bash
cd /opt/legal_mind
sudo -u legal python3 -m venv venv
sudo -u legal ./venv/bin/pip install --upgrade pip
sudo -u legal ./venv/bin/pip install -r requirements.txt
```

## 7. Проверка вручную

```bash
cd /opt/legal_mind
sudo -u legal ./venv/bin/gunicorn -b 127.0.0.1:5000 -w 2 app:app
```

Должно появиться `Listening at: http://127.0.0.1:5000`. В другом окне SSH:

```bash
curl http://127.0.0.1:5000/health
```

Ожидаемый ответ: `{"status":"ok","llm_configured":true}`.

Если `llm_configured:false` — проверь `.env`.

Ctrl+C — остановить.

## 8. systemd-сервис

Создай `/etc/systemd/system/legal-mind.service`:

```ini
[Unit]
Description=Legal Mind Web
After=network.target

[Service]
Type=simple
User=legal
WorkingDirectory=/opt/legal_mind
EnvironmentFile=/opt/legal_mind/.env
ExecStart=/opt/legal_mind/venv/bin/gunicorn -b 127.0.0.1:5000 -w 2 --timeout 60 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Активируй:

```bash
systemctl daemon-reload
systemctl enable legal-mind
systemctl start legal-mind
systemctl status legal-mind
```

Должно быть `active (running)`. Если упало:

```bash
journalctl -u legal-mind -n 50 --no-pager
```

## 9. Nginx как reverse proxy

Создай `/etc/nginx/sites-available/legal-mind`:

```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name 201.24.49.121;

    client_max_body_size 2M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

Активируй:

```bash
ln -sf /etc/nginx/sites-available/legal-mind /etc/nginx/sites-enabled/legal-mind
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
```

## 10. Firewall (если включён)

```bash
ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable
```

## 11. Проверка

Открой в браузере:

```
http://201.24.49.121/
```

Должна открыться форма. Заполни тестовые данные → скачается PDF.

## 12. Обновление после правок кода

Автодеплой:

    git push origin main

GitHub Actions → SSH → git pull → chmod → restart → health check.

Резерв (если Actions недоступен):

    .\deploy\deploy.ps1

## 13. Логи и диагностика

```bash
# логи приложения
journalctl -u legal-mind -n 100 --no-pager

# логи nginx
tail -f /var/log/nginx/error.log

# проверка портов
ss -tlnp | grep 5000
ss -tlnp | grep 80
```

## 14. Если что-то не работает

**Сайт не открывается по http://201.24.49.121/**
- `systemctl status nginx` — nginx запущен?
- `ufw status` — порт 80 разрешён?
- `ss -tlnp | grep 80` — nginx слушает?

**Ошибка 502 Bad Gateway**
- `systemctl status legal-mind` — сервис жив?
- `journalctl -u legal-mind -n 50` — что в логах?

**PDF не скачивается**
- `fc-list | grep -i dejavu` — шрифт установлен?
- Если нет: `apt install fonts-dejavu && systemctl restart legal-mind`

**`llm_configured: false`**
- Проверь `/opt/legal_mind/.env`:
  ```
  YANDEX_API_KEY=...
  YANDEX_FOLDER_ID=...
  ```
- `systemctl show legal-mind | grep EnvironmentFile`
- После правки `.env`: `systemctl restart legal-mind`

## Стоимость

- VPS Timeweb Cloud: ~200–400 ₽/мес.
- YandexGPT: ~0.2–0.4 ₽ за один запрос.
- Домен не нужен — работаем по IP `201.24.49.121`.