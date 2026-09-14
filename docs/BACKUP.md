# Legal Mind — Backup cases.db

Ежедневный бэкап SQLite-базы CASE в Yandex Object Storage.

## Что делает

- `scripts/backup_db.py`:
  1. `sqlite3 .backup()` — атомарная копия БД (безопасно при читателях)
  2. gzip (compresslevel 9)
  3. **шифрование `openssl enc -aes-256-cbc -pbkdf2 -iter 100000`**
  4. upload в `s3://legal-mind-backups/daily/cases_YYYY-MM-DD_HHMMSS.db.gz.enc`
  5. cleanup объектов старше `BACKUP_RETENTION_DAYS` дней (по умолчанию 30)

**Почему шифрование:** в `cases.db` — ПДн (ФИО, адрес, телефон,
суть конфликта). S3 — чужое облако, даже приватный бакет = не наш
контроль. Шифруем **до** upload, чтобы даже утечка ключей S3 не
дала доступа к данным.

**Пароль** — в `.env.backup` (`BACKUP_ENCRYPTION_PASSWORD`).
Сгенерирован `openssl rand -base64 32`. Хранить в менеджере
паролей (Bitwarden/KeePass). **Без пароля бэкапы не расшифровать
никогда.**

## Конфиг на сервере

`/opt/legal_mind/.env.backup` (chmod 600, owner legal):

    YC_S3_KEY_ID=...
    YC_S3_SECRET=...
    YC_S3_BUCKET=legal-mind-backups
    BACKUP_RETENTION_DAYS=30

Ключи Yandex Cloud берутся из Console → IAM → Сервисные аккаунты →
статический ключ доступа. Сервисному аккаунту нужна роль `storage.editor`.

## Как развернуть с нуля

1. Создать бакет `legal-mind-backups` (приватный, ru-central1)
2. Создать сервисный аккаунт `legal-mind-backup` с ролью `storage.editor`
3. Создать статический ключ доступа (сохранить ID и Secret)
4. На сервере создать `/opt/legal_mind/.env.backup`:

    cat > /opt/legal_mind/.env.backup << 'EOF'
    YC_S3_KEY_ID=<access_key_id>
    YC_S3_SECRET=<secret>
    YC_S3_BUCKET=legal-mind-backups
    BACKUP_RETENTION_DAYS=30
    EOF
    chmod 600 /opt/legal_mind/.env.backup
    chown legal:legal /opt/legal_mind/.env.backup

5. Поставить boto3:

    sudo -u legal /opt/legal_mind/venv/bin/pip install boto3

6. Тестовый запуск:

    cd /opt/legal_mind
    sudo -u legal ./venv/bin/python scripts/backup_db.py

## Cron

`/etc/cron.d/legal-mind-backup`:

    # Ежедневный бэкап cases.db в Yandex Object Storage
    # 03:00 UTC = 06:00 МСК
    0 3 * * * legal cd /opt/legal_mind && /opt/legal_mind/venv/bin/python /opt/legal_mind/scripts/backup_db.py >> /opt/legal_mind/logs/backup.log 2>&1

Применить:

    chmod 644 /etc/cron.d/legal-mind-backup

## Восстановление из бэкапа

Скачать последний `.enc` (через Python-скрипт на сервере):

    cd /opt/legal_mind
    sudo -u legal ./venv/bin/python -c "
    import boto3, os
    from dotenv import load_dotenv
    load_dotenv('.env.backup')
    s3 = boto3.client('s3', endpoint_url='https://storage.yandexcloud.net',
        aws_access_key_id=os.getenv('YC_S3_KEY_ID'),
        aws_secret_access_key=os.getenv('YC_S3_SECRET'), region_name='ru-central1')
    r = s3.list_objects_v2(Bucket=os.getenv('YC_S3_BUCKET'), Prefix='daily/')
    items = sorted(r.get('Contents', []), key=lambda x: x['LastModified'])
    s3.download_file(os.getenv('YC_S3_BUCKET'), items[-1]['Key'], '/tmp/backup.enc')
    print('OK:', items[-1]['Key'])
    "

Расшифровать (пароль из .env.backup):

    cd /opt/legal_mind
    PWD=$(grep '^BACKUP_ENCRYPTION_PASSWORD=' .env.backup | cut -d= -f2)
    openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
        -in /tmp/backup.enc -out /tmp/backup.db.gz \
        -pass "pass:$PWD"

Распаковать:

    gunzip /tmp/backup.db.gz

Остановить сервис, положить файл, запустить:

    systemctl stop legal-mind
    cp cases_YYYY-MM-DD_HHMMSS.db /opt/legal_mind/web/cases.db
    chown legal:legal /opt/legal_mind/web/cases.db
    chmod 600 /opt/legal_mind/web/cases.db
    systemctl start legal-mind

## Пароль шифрования: Yandex Lockbox

**Работает с 14.09.2026.** Пароль шифрования НЕ хранится в
`.env.backup` — тянется из Yandex Lockbox по REST API.

**Компоненты:**
- `core/lockbox.py` — чтение секретов через REST API
  (`payload.lockbox.api.cloud.yandex.net`), без SDK.
  IAM-токен кэшируется на 11 часов (живёт 12)
- Авторизация: authorized key сервисного аккаунта
  `legal-mind-backup` (`/opt/legal_mind/sa-key.json`, chmod 600)
- Secret ID: `e6qoscc5gjf12n81vsf9`
- Ключ в секрете: `BACKUP_ENCRYPTION_PASSWORD`
- Fallback: если Lockbox недоступен, `backup_db.py` берёт пароль
  из `BACKUP_ENCRYPTION_PASSWORD` в `.env.backup` (на сервере не задан,
  остаётся на случай аварии)

**Обёртка `scripts/run_backup.sh`:** cron зовёт её, а не python напрямую.
Она делает `cd` в корень проекта + `exec` python из venv.
Это устраняет проблему «то работает, то нет» — гонку с автодеплоем
`git reset --hard` (файл на секунду пропадает).

**Ротация пароля:** через UI Lockbox. При ротации создаётся **новая
версия** секрета. Старые бэкапы расшифровываются **старой версией**,
новые — новой. Если надо сохранить доступ к старым — не удаляй
предыдущие версии секрета.

**Плюсы:**
- `.env.backup` не содержит пароль шифрования
- Ротация через Lockbox UI (без SSH)
- Аудит доступа к секретам
- Тот же паттерн можно применить к `YANDEX_API_KEY` в `web/.env`

**Осторожно:** если потерять доступ к Yandex Cloud аккаунту —
потеряешь и S3, и Lockbox одновременно. Одна копия пароля
где-то **вне** Yandex (в Bitwarden/KeePass) — обязательна.

## Что НЕ бэкапится

- `web/.env` — секреты, восстанавливаются вручную
- `web/static/` — в git
- `region/data/*.db` — в git (или пересобираются скриптами)
- логи — не критичны

## Проверка что бэкапы идут

    ls -la /opt/legal_mind/logs/backup.log
    tail -20 /opt/legal_mind/logs/backup.log

Или в консоли Object Storage: бакет `legal-mind-backups` → `daily/`.