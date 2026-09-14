"""Health-check Cloud Function для Legal Mind.

Дёргает http://.../health раз в 5 минут (через Timer Trigger).
При падении — шлёт уведомление в Telegram.

Антифлуд через Object Storage: пишет state.json с последним статусом,
шлёт алерт только при СМЕНЕ статуса (ok→fail или fail→ok).

Переменные окружения:
  HEALTH_URL              — URL /health прода (default: http://201.24.49.121/health)
  TELEGRAM_BOT_TOKEN      — токен бота (@BotFather)
  TELEGRAM_CHAT_ID        — ID чата/канала для алертов
  YC_S3_KEY_ID            — статический ключ сервисного аккаунта
  YC_S3_SECRET            — секрет ключа
  YC_S3_BUCKET            — бакет (default: legal-mind-backups)
  YC_S3_STATE_KEY         — ключ файла состояния (default: monitoring/state.json)
"""

import json
import logging
import os
from datetime import datetime, timezone

import boto3
import requests
from botocore.client import Config
from botocore.exceptions import ClientError


log = logging.getLogger()
log.setLevel(logging.INFO)

HEALTH_URL = os.environ.get("HEALTH_URL", "http://201.24.49.121/health")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
S3_BUCKET = os.environ.get("YC_S3_BUCKET", "legal-mind-backups")
STATE_KEY = os.environ.get("YC_S3_STATE_KEY", "monitoring/state.json")
CHECK_TIMEOUT = 10


def _s3():
    return boto3.client(
        "s3",
        endpoint_url="https://storage.yandexcloud.net",
        aws_access_key_id=os.environ.get("YC_S3_KEY_ID", ""),
        aws_secret_access_key=os.environ.get("YC_S3_SECRET", ""),
        region_name="ru-central1",
        config=Config(signature_version="s3v4"),
    )


def _read_state(s3) -> dict:
    try:
        r = s3.get_object(Bucket=S3_BUCKET, Key=STATE_KEY)
        return json.loads(r["Body"].read().decode("utf-8"))
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "NoSuchKey":
            return {"status": "unknown", "changed_at": None}
        log.warning("Ошибка чтения state: %s", e)
        return {"status": "unknown", "changed_at": None}


def _write_state(s3, state: dict) -> None:
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=STATE_KEY,
            Body=json.dumps(state, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
    except ClientError as e:
        log.warning("Ошибка записи state: %s", e)


def _send_telegram(text: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        log.warning("Telegram не настроен (нет TELEGRAM_BOT_TOKEN/CHAT_ID)")
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        if r.status_code != 200:
            log.warning("Telegram вернул %s: %s", r.status_code, r.text[:200])
    except Exception as e:
        log.warning("Ошибка отправки в Telegram: %s", e)


def _check_health() -> tuple[bool, str]:
    """Returns (ok, detail)."""
    try:
        r = requests.get(HEALTH_URL, timeout=CHECK_TIMEOUT)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        try:
            j = r.json()
        except Exception:
            return False, "не JSON"
        if j.get("status") != "ok":
            return False, f"status={j.get('status')}"
        return True, "ok"
    except requests.Timeout:
        return False, f"timeout {CHECK_TIMEOUT}s"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def handler(event, context):
    """Точка входа Cloud Function (Timer Trigger)."""
    log.info("Health-check: %s", HEALTH_URL)
    s3 = _s3()
    state = _read_state(s3)
    prev_status = state.get("status", "unknown")

    ok, detail = _check_health()
    new_status = "ok" if ok else "fail"
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    log.info("Результат: %s (%s), было: %s", new_status, detail, prev_status)

    # Отправляем только при СМЕНЕ статуса (антифлуд)
    if new_status != prev_status:
        if new_status == "fail":
            msg = (
                f"🔴 <b>Legal Mind недоступен</b>\n\n"
                f"URL: {HEALTH_URL}\n"
                f"Ошибка: {detail}\n"
                f"Время (UTC): {now_iso}"
            )
            _send_telegram(msg)
        elif new_status == "ok" and prev_status == "fail":
            msg = (
                f"🟢 <b>Legal Mind восстановлен</b>\n\n"
                f"URL: {HEALTH_URL}\n"
                f"Время (UTC): {now_iso}"
            )
            _send_telegram(msg)

        _write_state(s3, {"status": new_status, "changed_at": now_iso, "detail": detail})

    return {
        "statusCode": 200,
        "body": json.dumps({"status": new_status, "detail": detail, "prev": prev_status}),
    }