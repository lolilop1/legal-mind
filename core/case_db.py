"""Абстракция доступа к БД CASE.

Всё взаимодействие с cases.db идёт через этот модуль.
Правило: никаких прямых SQL в app.py.

Путь: web/cases.db (права 600).
Переопределяется через переменную окружения CASE_DB_PATH (для тестов).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import stat
from datetime import date, datetime
from pathlib import Path

from core.case_id import generate_case_uuid, format_case_number, is_valid_uuid


log = logging.getLogger("legal_mind")

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent

DB_PATH = os.environ.get("CASE_DB_PATH") or str(_PROJECT_ROOT / "web" / "cases.db")
SCHEMA_PATH = str(_PROJECT_ROOT / "web" / "schema.sql")

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is not None:
        return _conn
    # isolation_level=None -> autocommit, транзакциями управляем сами (см. create_case)
    _conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA foreign_keys = ON")
    _conn.execute("PRAGMA busy_timeout = 5000")
    return _conn


def init_db() -> None:
    """Создаёт схему и устанавливает права 600."""
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Не найден schema.sql: {SCHEMA_PATH}")

    conn = _get_conn()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()

    try:
        os.chmod(DB_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as e:
        log.warning("Не удалось установить права 600 на %s: %s", DB_PATH, e)


def _next_seq_for_today(conn: sqlite3.Connection) -> int:
    today_prefix = f"LM-{date.today().strftime('%Y%m%d')}-"
    cur = conn.execute(
        "SELECT MAX(CAST(SUBSTR(case_number, -4) AS INTEGER)) "
        "FROM cases WHERE case_number LIKE ?",
        (today_prefix + "%",),
    )
    row = cur.fetchone()
    current_max = row[0] if row and row[0] is not None else 0
    return current_max + 1


def create_case(
    problem_type: str,
    source_text: str,
    user_data: dict,
    dna: dict | None = None,
    engine_version: str = "",
    rules_version: str = "",
    template_version: str = "",
) -> dict:
    """Создаёт новый CASE. Возвращает {case_number, case_uuid, created_at}.

    Генерация номера + вставка — атомарны (BEGIN IMMEDIATE), с ретраем
    при коллизии case_number между параллельными запросами.
    """
    conn = _get_conn()
    dna = dna or {}

    def j(v):
        if v is None or v == "" or v == [] or v == {}:
            return None
        return json.dumps(v, ensure_ascii=False)

    last_error: Exception | None = None

    for _attempt in range(5):
        conn.execute("BEGIN IMMEDIATE")
        try:
            seq = _next_seq_for_today(conn)
            case_number = format_case_number(date.today(), seq)
            case_uuid = generate_case_uuid()
            now = datetime.now().isoformat(timespec="seconds")

            conn.execute(
                """
                INSERT INTO cases (
                    case_number, case_uuid, created_at, updated_at,
                    problem_type, subject, object, event, dates, amount,
                    counterparty, jurisdiction, demand,
                    evidence, confidence, trace,
                    engine_version, rules_version, template_version,
                    source_text, user_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_number, case_uuid, now, now,
                    problem_type,
                    dna.get("subject"),
                    dna.get("object"),
                    dna.get("event"),
                    j(dna.get("dates")),
                    dna.get("amount"),
                    dna.get("counterparty"),
                    dna.get("jurisdiction"),
                    dna.get("demand"),
                    j(dna.get("evidence")),
                    j(dna.get("confidence")),
                    j(dna.get("trace")),
                    engine_version or None,
                    rules_version or None,
                    template_version or None,
                    source_text,
                    json.dumps(user_data, ensure_ascii=False),
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            conn.rollback()
            last_error = e
            continue
        except Exception:
            conn.rollback()
            raise

        add_event(case_number, "created", {"problem_type": problem_type})
        return {"case_number": case_number, "case_uuid": case_uuid, "created_at": now}

    raise RuntimeError(
        f"Не удалось создать CASE — коллизия case_number 5 раз подряд: {last_error}"
    )


def get_case(case_number: str, case_uuid: str) -> dict | None:
    """Возвращает CASE по паре (номер + UUID) или None."""
    if not case_number or not case_uuid:
        return None
    if not is_valid_uuid(case_uuid):
        return None

    conn = _get_conn()
    cur = conn.execute(
        "SELECT * FROM cases WHERE case_number = ? AND case_uuid = ?",
        (case_number, case_uuid),
    )
    row = cur.fetchone()
    if row is None:
        return None

    case = dict(row)
    for field in ("dates", "evidence", "confidence", "trace", "user_data"):
        if case.get(field):
            try:
                case[field] = json.loads(case[field])
            except json.JSONDecodeError:
                pass
    return case


def update_case(case_number: str, case_uuid: str, updates: dict) -> bool:
    case = get_case(case_number, case_uuid)
    if case is None:
        return False

    allowed = {
        "subject", "object", "event", "dates", "amount",
        "counterparty", "jurisdiction", "demand",
        "evidence", "confidence", "trace",
    }
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return False

    for k, v in fields.items():
        if isinstance(v, (dict, list)):
            fields[k] = json.dumps(v, ensure_ascii=False)

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values())
    values.append(datetime.now().isoformat(timespec="seconds"))
    values.extend([case_number, case_uuid])

    conn = _get_conn()
    conn.execute(
        f"UPDATE cases SET {set_clause}, updated_at = ? "
        f"WHERE case_number = ? AND case_uuid = ?",
        values,
    )
    conn.commit()

    add_event(case_number, "updated", {"fields": list(fields.keys())})
    return True


def add_document(
    case_number: str,
    doc_type: str,
    content: bytes,
    template_version: str = "",
    engine_version: str = "",
) -> int:
    conn = _get_conn()
    cur = conn.execute(
        """
        INSERT INTO case_documents (
            case_number, doc_type, content, generated_at,
            template_version, engine_version
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            case_number,
            doc_type,
            content,
            datetime.now().isoformat(timespec="seconds"),
            template_version or None,
            engine_version or None,
        ),
    )
    conn.commit()

    add_event(case_number, "generated", {"doc_type": doc_type})
    return cur.lastrowid


def get_documents(case_number: str) -> list[dict]:
    conn = _get_conn()
    cur = conn.execute(
        "SELECT id, doc_type, generated_at, template_version, engine_version "
        "FROM case_documents WHERE case_number = ? ORDER BY generated_at",
        (case_number,),
    )
    return [dict(r) for r in cur.fetchall()]


def get_document_content(doc_id: int, case_number: str) -> bytes | None:
    """Возвращает содержимое документа только если он принадлежит указанному делу."""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT content FROM case_documents WHERE id = ? AND case_number = ?",
        (doc_id, case_number),
    )
    row = cur.fetchone()
    return row["content"] if row else None


def add_event(case_number: str, event_type: str, event_data: dict | None = None) -> int:
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO case_events (case_number, event_type, event_data, created_at) "
        "VALUES (?, ?, ?, ?)",
        (
            case_number,
            event_type,
            json.dumps(event_data or {}, ensure_ascii=False),
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_events(case_number: str, limit: int = 50) -> list[dict]:
    conn = _get_conn()
    cur = conn.execute(
        "SELECT event_type, event_data, created_at FROM case_events "
        "WHERE case_number = ? ORDER BY created_at DESC LIMIT ?",
        (case_number, limit),
    )
    return [dict(r) for r in cur.fetchall()]


def list_cases_for_date(day: date | None = None, limit: int = 100) -> list[dict]:
    """Для отладки: список CASE за дату (без UUID)."""
    if day is None:
        day = date.today()
    prefix = f"LM-{day.strftime('%Y%m%d')}-%"
    conn = _get_conn()
    cur = conn.execute(
        "SELECT case_number, created_at, problem_type, jurisdiction, demand "
        "FROM cases WHERE case_number LIKE ? "
        "ORDER BY created_at DESC LIMIT ?",
        (prefix, limit),
    )
    return [dict(r) for r in cur.fetchall()]


def delete_case(case_number: str, case_uuid: str) -> bool:
    """Удаляет CASE (право пользователя по 152-ФЗ)."""
    if get_case(case_number, case_uuid) is None:
        return False
    conn = _get_conn()
    conn.execute(
        "DELETE FROM cases WHERE case_number = ? AND case_uuid = ?",
        (case_number, case_uuid),
    )
    conn.commit()
    return True


def stats() -> dict:
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    by_type = dict(conn.execute(
        "SELECT problem_type, COUNT(*) FROM cases GROUP BY problem_type"
    ).fetchall())
    return {"total": total, "by_type": by_type}