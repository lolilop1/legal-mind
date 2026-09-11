"""Legal Mind — phone number validation."""

from __future__ import annotations

import re


_DIGITS_RE = re.compile(r"\d")


def _extract_digits(raw: str) -> str:
    return "".join(_DIGITS_RE.findall(raw or ""))


def _is_all_same(digits: str) -> bool:
    return len(set(digits)) == 1


def _is_sequential(digits: str) -> bool:
    if len(digits) < 6:
        return False
    asc = "0123456789" * 2
    desc = "9876543210" * 2
    return digits in asc or digits in desc


def validate_phone(raw: str) -> tuple[bool, str]:
    digits = _extract_digits(raw)

    if not digits:
        return False, "Укажите контактный телефон — без него заявление не примут."

    if len(digits) < 10:
        return False, (
            "Телефон слишком короткий. Укажите полный номер, "
            "например: +7 (999) 123-45-67."
        )

    if len(digits) > 15:
        return False, "Телефон слишком длинный. Укажите один номер без лишних цифр."

    if _is_all_same(digits):
        return False, (
            "Похоже, номер ненастоящий (все цифры одинаковые). "
            "Укажите реальный контактный телефон."
        )

    if _is_sequential(digits):
        return False, (
            "Похоже, номер ненастоящий (цифры идут по порядку). "
            "Укажите реальный контактный телефон."
        )

    return True, ""
