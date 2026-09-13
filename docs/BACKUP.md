# Legal Mind — Backup cases.db

Ежедневный бэкап SQLite-базы CASE в Yandex Object Storage.

## Что делает

- `scripts/backup_db.py`:
  1. `sqlite3 .backup()` — атомарная копия БД (безопасно при читателях)
  2. gzip
  3. upload в `s3://legal-mind-backups/daily/cases_YYYY-MM-DD_HHMMSS.db.gz`
  4. cleanup объектов старше `BACKUP_RETENTION_DAYS` дней (по умолчанию 30)

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

Скачать:

    cd /tmp
    aws --endpoint-url=https://storage.yandexcloud.net \
        s3 cp s3://legal-mind-backups/daily/cases_YYYY-MM-DD_HHMMSS.db.gz . \
        --profile yc

(или через консоль Object Storage)

Распаковать:

    gunzip cases_YYYY-MM-DD_HHMMSS.db.gz

Остановить сервис, положить файл, запустить:

    systemctl stop legal-mind
    cp cases_YYYY-MM-DD_HHMMSS.db /opt/legal_mind/web/cases.db
    chown legal:legal /opt/legal_mind/web/cases.db
    chmod 600 /opt/legal_mind/web/cases.db
    systemctl start legal-mind

## Что НЕ бэкапится

- `web/.env` — секреты, восстанавливаются вручную
- `web/static/` — в git
- `region/data/*.db` — в git (или пересобираются скриптами)
- логи — не критичны

## Проверка что бэкапы идут

    ls -la /opt/legal_mind/logs/backup.log
    tail -20 /opt/legal_mind/logs/backup.log

Или в консоли Object Storage: бакет `legal-mind-backups` → `daily/`.