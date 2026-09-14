# -*- coding: utf-8 -*-
"""Тесты health_check Cloud Function. Моки requests + boto3."""

import _bootstrap  # noqa: F401

import json
import os
import sys
from unittest.mock import MagicMock, patch


# Отключаем реальные сеть/облако до импорта
os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
os.environ["TELEGRAM_CHAT_ID"] = "123456"
os.environ["YC_S3_KEY_ID"] = "test-key"
os.environ["YC_S3_SECRET"] = "test-secret"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "deploy", "health_check"))

import index as hc


def main():
    passed = 0
    failed = 0

    def check(cond, label):
        nonlocal passed, failed
        if cond:
            print(f"[PASS] {label}")
            passed += 1
        else:
            print(f"[FAIL] {label}")
            failed += 1

    # ═══ 1. _check_health: OK ═══
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"status": "ok"}
    with patch.object(hc.requests, "get", return_value=fake_resp):
        ok, detail = hc._check_health()
    check(ok is True, "check_health: 200 + status=ok → True")
    check(detail == "ok", "check_health: detail=ok")

    # ═══ 2. _check_health: HTTP 500 ═══
    fake_500 = MagicMock()
    fake_500.status_code = 500
    with patch.object(hc.requests, "get", return_value=fake_500):
        ok, detail = hc._check_health()
    check(ok is False, "check_health: 500 → False")
    check("500" in detail, f"check_health: detail содержит 500 ({detail})")

    # ═══ 3. _check_health: status != ok ═══
    fake_bad = MagicMock()
    fake_bad.status_code = 200
    fake_bad.json.return_value = {"status": "degraded"}
    with patch.object(hc.requests, "get", return_value=fake_bad):
        ok, detail = hc._check_health()
    check(ok is False, "check_health: status=degraded → False")

    # ═══ 4. _check_health: timeout ═══
    with patch.object(hc.requests, "get", side_effect=hc.requests.Timeout()):
        ok, detail = hc._check_health()
    check(ok is False, "check_health: Timeout → False")
    check("timeout" in detail.lower(), f"check_health: detail 'timeout' ({detail})")

    # ═══ 5. _check_health: connection error ═══
    with patch.object(hc.requests, "get", side_effect=ConnectionError("no route")):
        ok, detail = hc._check_health()
    check(ok is False, "check_health: ConnectionError → False")
    check("ConnectionError" in detail, f"check_health: detail содержит тип ({detail})")

    # ═══ 6. _read_state: пусто → unknown ═══
    fake_s3 = MagicMock()
    from botocore.exceptions import ClientError
    err = ClientError({"Error": {"Code": "NoSuchKey"}}, "get_object")
    fake_s3.get_object.side_effect = err
    state = hc._read_state(fake_s3)
    check(state["status"] == "unknown", "read_state: NoSuchKey → unknown")

    # ═══ 7. _read_state: есть state ═══
    fake_s3b = MagicMock()
    fake_s3b.get_object.return_value = {"Body": MagicMock(read=lambda: json.dumps({
        "status": "fail", "changed_at": "2026-01-01T00:00:00Z"
    }).encode())}
    state = hc._read_state(fake_s3b)
    check(state["status"] == "fail", "read_state: читает fail")

    # ═══ 8. _send_telegram: не настроен → не падает ═══
    old_tok = hc.BOT_TOKEN
    hc.BOT_TOKEN = ""
    try:
        hc._send_telegram("test")
        check(True, "send_telegram: без токена не падает")
    except Exception as e:
        check(False, f"send_telegram: упало ({e})")
    finally:
        hc.BOT_TOKEN = old_tok

    # ═══ 9. handler: OK → OK, без алерта ═══
    fake_resp2 = MagicMock()
    fake_resp2.status_code = 200
    fake_resp2.json.return_value = {"status": "ok"}

    with patch.object(hc, "_s3") as mock_s3, \
         patch.object(hc, "_read_state", return_value={"status": "ok"}), \
         patch.object(hc, "_write_state") as mock_write, \
         patch.object(hc, "_check_health", return_value=(True, "ok")), \
         patch.object(hc, "_send_telegram") as mock_tg:
        result = hc.handler({}, None)

    body = json.loads(result["body"])
    check(result["statusCode"] == 200, "handler: statusCode 200")
    check(body["status"] == "ok", "handler: status=ok")
    check(mock_tg.call_count == 0, "handler: без смены статуса — нет алерта")
    check(mock_write.call_count == 0, "handler: без смены статуса — нет записи state")

    # ═══ 10. handler: ok → fail → алерт + state ═══
    with patch.object(hc, "_s3"), \
         patch.object(hc, "_read_state", return_value={"status": "ok"}), \
         patch.object(hc, "_write_state") as mock_write2, \
         patch.object(hc, "_check_health", return_value=(False, "timeout 10s")), \
         patch.object(hc, "_send_telegram") as mock_tg2:
        result = hc.handler({}, None)

    body = json.loads(result["body"])
    check(body["status"] == "fail", "handler: fail зафиксирован")
    check(mock_tg2.call_count == 1, "handler: алерт отправлен при ok→fail")
    check(mock_write2.call_count == 1, "handler: state записан")

    # ═══ 11. handler: fail → ok → «восстановлен» ═══
    with patch.object(hc, "_s3"), \
         patch.object(hc, "_read_state", return_value={"status": "fail"}), \
         patch.object(hc, "_write_state"), \
         patch.object(hc, "_check_health", return_value=(True, "ok")), \
         patch.object(hc, "_send_telegram") as mock_tg3:
        result = hc.handler({}, None)

    check(mock_tg3.call_count == 1, "handler: алерт 'восстановлен' при fail→ok")

    # ═══ 12. handler: fail → fail → без алерта (антифлуд) ═══
    with patch.object(hc, "_s3"), \
         patch.object(hc, "_read_state", return_value={"status": "fail"}), \
         patch.object(hc, "_write_state"), \
         patch.object(hc, "_check_health", return_value=(False, "timeout")), \
         patch.object(hc, "_send_telegram") as mock_tg4:
        hc.handler({}, None)

    check(mock_tg4.call_count == 0, "handler: fail→fail без алерта (антифлуд)")

    print(f"\nTotal: {passed + failed}  Passed: {passed}  Failed: {failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()