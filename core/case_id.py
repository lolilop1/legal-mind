"""Генерация идентификаторов CASE.

Формат номера: LM-YYYYMMDD-NNNN
- LM        — префикс Legal Mind
- YYYYMMDD  — дата создания
- NNNN      — порядковый номер за день (0001-9999)

UUID: 32 hex-символа (uuid4). Криптостойкий, непредсказуемый.
Доступ к делу — только по паре (номер + UUID).
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime


_CASE_NUMBER_RE = re.compile(r"^LM-(\d{8})-(\d{4})$")


def generate_case_uuid() -> str:
    """32 hex-символа. Криптостойкий."""
    return uuid.uuid4().hex


def format_case_number(day: date | None = None, seq: int = 1) -> str:
    """LM-YYYYMMDD-NNNN."""
    if day is None:
        day = date.today()
    if not 1 <= seq <= 9999:
        raise ValueError(f"seq должен быть в диапазоне 1..9999, получено {seq}")
    return f"LM-{day.strftime('%Y%m%d')}-{seq:04d}"


def parse_case_number(case_number: str) -> tuple[date, int] | None:
    """Разбирает номер в (дата, seq). None если формат неверный."""
    m = _CASE_NUMBER_RE.match(case_number)
    if not m:
        return None
    try:
        d = datetime.strptime(m.group(1), "%Y%m%d").date()
        seq = int(m.group(2))
        return d, seq
    except ValueError:
        return None


def is_valid_uuid(case_uuid: str) -> bool:
    """Проверка формата UUID (32 hex)."""
    if not case_uuid or len(case_uuid) != 32:
        return False
    try:
        int(case_uuid, 16)
        return True
    except ValueError:
        return False