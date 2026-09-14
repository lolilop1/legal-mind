"""Чтение секретов из Yandex Lockbox через REST API.

Без SDK — только requests + pyjwt. IAM-токен кэшируется на 11 часов.

Использование:
    from core.lockbox import get_secret_value
    pwd = get_secret_value("e6qoscc5gjf12n81vsf9", "BACKUP_ENCRYPTION_PASSWORD")

Авторизация: authorized key сервисного аккаунта (JSON файл).
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import jwt  # PyJWT
import requests


log = logging.getLogger("legal_mind")

_SA_KEY_PATH = Path("/opt/legal_mind/sa-key.json")
_IAM_URL = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
_LOCKBOX_URL = "https://payload.lockbox.api.cloud.yandex.net/lockbox/v1/secrets/{sid}/payload"

# Кэш IAM-токена: он живёт 12 часов, мы обновляем на 11-й
_token_cache: dict[str, object] = {"token": None, "expires_at": 0}


def _load_sa_key() -> dict:
    if not _SA_KEY_PATH.exists():
        raise FileNotFoundError(f"Не найден authorized key: {_SA_KEY_PATH}")
    with open(_SA_KEY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _make_jwt(sa_key: dict) -> str:
    """Формирует JWT для обмена на IAM-токен."""
    now = int(time.time())
    payload = {
        "aud": _IAM_URL,
        "iss": sa_key["service_account_id"],
        "iat": now,
        "exp": now + 3600,  # JWT живёт 1 час
    }
    headers = {
        "kid": sa_key["id"],  # key_id
    }
    # Приватный ключ из JSON — уже в PEM формате
    return jwt.encode(
        payload,
        sa_key["private_key"],
        algorithm="PS256",
        headers=headers,
    )


def _get_iam_token(force_refresh: bool = False) -> str:
    """Возвращает IAM-токен. Кэширует на 11 часов."""
    now = time.time()
    if not force_refresh and _token_cache["token"] and now < _token_cache["expires_at"]:
        return str(_token_cache["token"])

    sa_key = _load_sa_key()
    jwk = _make_jwt(sa_key)

    resp = requests.post(
        _IAM_URL,
        json={"jwt": jwk},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data["iamToken"]
    # Обновляем за час до истечения (12ч жизни токена)
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + 11 * 3600
    log.info("IAM-токен получен, действует до %s", data.get("expiresAt", "?"))
    return token


def get_secret_value(secret_id: str, key: str) -> str:
    """Читает одно значение из Lockbox по key.

    Args:
        secret_id: ID секрета в Lockbox
        key: имя ключа внутри секрета

    Returns:
        Значение ключа как строка.

    Raises:
        KeyError: если ключа нет в секрете
        requests.HTTPError: если API вернул ошибку
    """
    token = _get_iam_token()
    url = _LOCKBOX_URL.format(sid=secret_id)
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if resp.status_code == 401:
        # Токен протух — обновим один раз
        token = _get_iam_token(force_refresh=True)
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
    resp.raise_for_status()
    data = resp.json()
    for entry in data.get("entries", []):
        if entry.get("key") == key:
            # Текст лежит в textValue, бинарь — в binaryValue (base64)
            return entry.get("textValue") or ""
    raise KeyError(f"Ключ {key!r} не найден в секрете {secret_id!r}")