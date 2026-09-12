"""Legal Mind — phone number validation and normalization."""

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


def _is_russian_number(digits: str) -> bool:
    """Похоже ли на российский номер (10 или 11 цифр, начинается с 7/8 при 11)."""
    if len(digits) == 10:
        return True
    if len(digits) == 11 and digits[0] in ("7", "8"):
        return True
    return False


def normalize_phone(raw: str) -> str:
    """Приводит номер к формату +7 (XXX) XXX-XX-XX (для РФ).

    Для иностранных номеров (10 и меньше цифр, не РФ, или 11+ не с 7/8)
    возвращает исходное представление в виде строки цифр с ведущим +,
    если это возможно.

    Пример:
        "+7 987 908 90 86" → "+7 (987) 908-90-86"
        "89879089086"      → "+7 (987) 908-90-86"
        "9879089086"       → "+7 (987) 908-90-86"
        "123456789012345"  → "+123456789012345"
        ""                 → ""
    """
    digits = _extract_digits(raw)
    if not digits:
        return ""

    stripped = (raw or "").strip()

    # Явный иностранный: начинается с "+" и не "+7"
    if stripped.startswith("+") and not stripped.startswith("+7"):
        return "+" + digits

    # Российский номер — приводим к канонической форме
    if len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"

    if len(digits) == 11 and digits[0] in ("7", "8"):
        body = digits[1:]
        return f"+7 ({body[0:3]}) {body[3:6]}-{body[6:8]}-{body[8:10]}"

    # Иностранный или странный — просто +цифры
    return "+" + digits


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

    # Усиленная проверка РФ-номеров
    if len(digits) in (12, 13, 14, 15) and digits[0] in ("7", "8"):
        return False, (
            "Похоже, в номере лишние цифры. Для российского номера "
            "нужно 10 цифр (без кода страны) или 11 с кодом "
            "(+7 или 8). Проверьте номер."
        )

    return True, ""
