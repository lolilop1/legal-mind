"""Ежедневный бэкап cases.db в Yandex Object Storage.

Читает .env.backup (YC_S3_KEY_ID, YC_S3_SECRET, YC_S3_BUCKET).
Делает SQLite .backup (атомарно, безопасно при работающих читателях),
заливает в S3 как cases_YYYY-MM-DD_HHMMSS.db.gz, удаляет старше N дней.

Запуск: python scripts/backup_db.py
Cron:   0 3 * * * cd /opt/legal_mind && ./venv/bin/python scripts/backup_db.py
"""

from __future__ import annotations

import gzip
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv


_ROOT = Path(__file__).resolve().parent.parent
_ENV_BACKUP = _ROOT / ".env.backup"
_DEFAULT_DB = _ROOT / "web" / "cases.db"

load_dotenv(dotenv_path=_ENV_BACKUP if _ENV_BACKUP.exists() else None)

YC_S3_KEY_ID = os.getenv("YC_S3_KEY_ID", "")
YC_S3_SECRET = os.getenv("YC_S3_SECRET", "")
YC_S3_BUCKET = os.getenv("YC_S3_BUCKET", "legal-mind-backups")
CASE_DB_PATH = os.getenv("CASE_DB_PATH") or str(_DEFAULT_DB)
RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

# Lockbox: пароль шифрования тянем из Yandex Lockbox по REST API.
# Fallback: если LOCKBOX_SECRET_ID не задан — берём из .env.backup
LOCKBOX_SECRET_ID = os.getenv("LOCKBOX_SECRET_ID", "e6qoscc5gjf12n81vsf9")
LOCKBOX_KEY = os.getenv("LOCKBOX_KEY", "BACKUP_ENCRYPTION_PASSWORD")


def _get_backup_password() -> str:
    """Пароль шифрования: из Lockbox, fallback — из .env.backup."""
    # Пытаемся из Lockbox
    try:
        from core.lockbox import get_secret_value
        pwd = get_secret_value(LOCKBOX_SECRET_ID, LOCKBOX_KEY)
        if pwd:
            log(f"пароль шифрования получен из Lockbox (secret_id={LOCKBOX_SECRET_ID})")
            return pwd
    except Exception as e:
        log(f"Lockbox недоступен: {type(e).__name__}: {e}")
        log("fallback на BACKUP_ENCRYPTION_PASSWORD из .env.backup")

    # Fallback: .env.backup
    pwd = os.getenv("BACKUP_ENCRYPTION_PASSWORD", "")
    if pwd:
        log("пароль взят из .env.backup (fallback)")
        return pwd

    raise RuntimeError(
        "Пароль шифрования недоступен: Lockbox не отвечает, "
        "и BACKUP_ENCRYPTION_PASSWORD не задан в .env.backup"
    )

ENDPOINT = "https://storage.yandexcloud.net"
PREFIX = "daily/"


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{ts} [backup] {msg}", flush=True)


def sqlite_backup(src: Path, dst: Path) -> None:
    """Атомарный бэкап SQLite. Безопасно при параллельных читателях."""
    import sqlite3
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst))
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()


def gzip_file(src: Path) -> Path:
    """Сжимает в .gz, удаляет исходник."""
    dst = src.with_suffix(src.suffix + ".gz")
    with open(src, "rb") as f_in, gzip.open(dst, "wb", compresslevel=9) as f_out:
        f_out.write(f_in.read())
    src.unlink()
    return dst


def encrypt_file(src: Path, password: str) -> Path:
    """Шифрует .gz в .gz.enc через openssl aes-256-cbc + pbkdf2."""
    if not password:
        raise RuntimeError("BACKUP_ENCRYPTION_PASSWORD не задан в .env.backup")

    dst = src.with_suffix(src.suffix + ".enc")
    # -pbkdf2 -iter 100000 → защита от брутфорса пароля
    cmd = [
        "openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "100000",
        "-salt",
        "-in", str(src),
        "-out", str(dst),
        "-pass", f"pass:{password}",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"openssl failed: {res.stderr}")
    src.unlink()  # удаляем незашифрованный .gz
    return dst


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=YC_S3_KEY_ID,
        aws_secret_access_key=YC_S3_SECRET,
        region_name="ru-central1",
        config=Config(signature_version="s3v4"),
    )


def upload(s3, local: Path, key: str) -> None:
    s3.upload_file(
        str(local), YC_S3_BUCKET, key,
        ExtraArgs={"ContentType": "application/gzip"},
    )


def cleanup_old(s3) -> int:
    """Удаляет объекты старше RETENTION_DAYS. Возвращает число удалённых."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    removed = 0
    try:
        resp = s3.list_objects_v2(Bucket=YC_S3_BUCKET, Prefix=PREFIX)
        for obj in resp.get("Contents", []):
            if obj["LastModified"] < cutoff:
                s3.delete_object(Bucket=YC_S3_BUCKET, Key=obj["Key"])
                log(f"удалён старый: {obj['Key']}")
                removed += 1
    except ClientError as e:
        log(f"ошибка cleanup: {e}")
    return removed


def main() -> int:
    if not YC_S3_KEY_ID or not YC_S3_SECRET:
        log("FAIL: YC_S3_KEY_ID / YC_S3_SECRET не заданы в .env.backup")
        return 1

    # Пароль проверим позже (Lockbox или fallback)
    # при вызове _get_backup_password()

    # Пароль проверим позже (Lockbox или fallback)
    # при вызове _get_backup_password()

    # Пароль проверим позже (Lockbox или fallback)
    # при вызове _get_backup_password()

    src = Path(CASE_DB_PATH)
    if not src.exists():
        log(f"FAIL: {src} не найден")
        return 1

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    key = f"{PREFIX}cases_{ts}.db.gz"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_db = Path(tmp) / "cases.db"
        log(f"sqlite .backup -> {tmp_db}")
        sqlite_backup(src, tmp_db)

        log("gzip...")
        tmp_gz = gzip_file(tmp_db)
        size_gz_kb = tmp_gz.stat().st_size // 1024
        log(f"сжатый размер: {size_gz_kb} КБ")

        log("encrypt (aes-256-cbc)...")
        pwd = _get_backup_password()
        tmp_enc = encrypt_file(tmp_gz, pwd)
        size_enc_kb = tmp_enc.stat().st_size // 1024
        log(f"зашифрованный размер: {size_enc_kb} КБ")

        # Меняем расширение в ключе: .db.gz -> .db.gz.enc
        key = key + ".enc" if not key.endswith(".enc") else key

        log(f"upload -> s3://{YC_S3_BUCKET}/{key}")
        try:
            s3 = s3_client()
            upload(s3, tmp_enc, key)
        except ClientError as e:
            log(f"FAIL upload: {e}")
            return 1

        log("cleanup старых...")
        removed = cleanup_old(s3)
        log(f"удалено: {removed}")

    log(f"OK: {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())