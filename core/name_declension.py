"""Legal Mind — ФИО declension to genitive case (via pymorphy3).

Example:
    "Иванов Иван Иванович"   -> "Иванова Ивана Ивановича"
    "Кузнецова Мария Ивановна" -> "Кузнецовой Марии Ивановны"

Uses pymorphy3 with explicit part-of-speech tags (Surn / Name / Patr) and
gender match (detected from patronymic) to pick the correct parse.
Restores capitalization. Falls back to the input on any failure.
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger("legal_mind")

try:
    import pymorphy3
    _MORPH = pymorphy3.MorphAnalyzer()
    _PYMORPHY_AVAILABLE = True
except ImportError:
    _MORPH = None
    _PYMORPHY_AVAILABLE = False
    log.warning("pymorphy3 не установлен — склонение ФИО отключено")


_CYRILLIC_RE = re.compile(r"^[А-ЯЁа-яё\-\s]+$")
# Именительный падеж
_FEMALE_MIDDLE_SUFFIXES = ("овна", "евна", "ична", "инична")
_MALE_MIDDLE_SUFFIXES = ("ович", "евич", "ич")
# Родительный падеж (уже склонённое ФИО — люди часто так вводят)
_FEMALE_MIDDLE_GENITIVE = ("овны", "евны", "ичны", "иничны")
_MALE_MIDDLE_GENITIVE = ("овича", "евича", "ича")


def _detect_gender(middle_name: str) -> str | None:
    """Определить род по отчеству. Работает и с именительным, и с родительным падежом."""
    lower = middle_name.lower()
    if lower.endswith(_FEMALE_MIDDLE_SUFFIXES) or lower.endswith(_FEMALE_MIDDLE_GENITIVE):
        return "femn"
    if lower.endswith(_MALE_MIDDLE_SUFFIXES) or lower.endswith(_MALE_MIDDLE_GENITIVE):
        return "masc"
    return None

def detect_gender_by_name(name: str) -> str | None:
    """Определяет пол по одному имени. 'Мария' -> 'femn', 'Пётр' -> 'masc'."""
    if not name or not _PYMORPHY_AVAILABLE:
        return None
    try:
        variants = _MORPH.parse(name)
        for v in variants:
            if "Name" in v.tag:
                if "femn" in v.tag:
                    return "femn"
                if "masc" in v.tag:
                    return "masc"
    except Exception:
        pass
    # Fallback: русские женские имена обычно на -а/-я/-ия
    lower = name.lower()
    if lower.endswith(("ия", "ья")):
        return "femn"
    if lower.endswith(("а", "я")):
        return "femn"
    return None


def detect_gender(fio: str) -> str | None:
    """Определяет пол по отчеству в ФИО.

    Returns: 'masc' | 'femn' | None
    Пример: "Иванов Иван Иванович" -> 'masc'
            "Иванова Мария Петровна" -> 'femn'
    """
    raw = (fio or "").strip()
    if not raw:
        return None
    parts = raw.split()
    if len(parts) < 3:
        return None
    return _detect_gender(parts[2])


def _inflect_genitive(word: str, kind: str | None = None,
                      gender: str | None = None) -> str:
    """Склоняет слово в родительный падеж.

    kind:   'Surn' | 'Name' | 'Patr' | None
    gender: 'masc' | 'femn' | None
    Восстанавливает заглавную первую букву. При неудаче возвращает вход.
    """
    if not word:
        return word
    try:
        variants = _MORPH.parse(word)

        def matches(v) -> bool:
            if kind is not None and kind not in v.tag:
                return False
            if gender is not None and gender not in v.tag:
                return False
            return True

        chosen = next((v for v in variants if matches(v)), None)
        if chosen is None and kind is not None:
            # Ослабляем: только kind
            chosen = next((v for v in variants if kind in v.tag), None)
        if chosen is None:
            chosen = variants[0]

        inflected = chosen.inflect({"gent"})
        if inflected is None:
            return word

        result = inflected.word
        if word[0].isupper():
            result = result[0].upper() + result[1:]
        return result
    except Exception as e:
        log.warning("Не удалось склонить слово %r: %s", word, e)
        return word


def decline_fio_dative(fio: str) -> str:
    """Склоняет ФИО в дательный падеж.

    Пример: "Иванов Иван Иванович" -> "Иванову Ивану Ивановичу"
            "Петрова Мария Ивановна" -> "Петровой Марии Ивановне"
    При неудаче возвращает вход без изменений.
    """
    raw = (fio or "").strip()
    if not raw:
        return raw
    if not _PYMORPHY_AVAILABLE:
        return raw
    if not _CYRILLIC_RE.match(raw):
        return raw

    parts = raw.split()
    if len(parts) not in (2, 3):
        return raw

    try:
        if len(parts) == 3:
            last_raw, first_raw, middle_raw = parts
            gender = _detect_gender(middle_raw)
            last = _inflect_dative(last_raw, kind="Surn", gender=gender)
            first = _inflect_dative(first_raw, kind="Name", gender=gender)
            middle = _inflect_dative(middle_raw, kind="Patr", gender=gender)
            return f"{last} {first} {middle}"
        else:
            # 2 части: Фамилия И.О. или Фамилия Имя — оставляем как есть
            return raw
    except Exception as e:
        log.warning("Не удалось склонить ФИО в дательный %r: %s", raw, e)
        return raw


def _inflect_dative(word: str, kind: str | None = None,
                    gender: str | None = None) -> str:
    """Склоняет слово в дательный падеж (datv). Аналог _inflect_genitive."""
    if not word:
        return word
    try:
        variants = _MORPH.parse(word)

        def matches(v) -> bool:
            if kind is not None and kind not in v.tag:
                return False
            if gender is not None and gender not in v.tag:
                return False
            return True

        chosen = next((v for v in variants if matches(v)), None)
        if chosen is None and kind is not None:
            chosen = next((v for v in variants if kind in v.tag), None)
        if chosen is None:
            chosen = variants[0]

        inflected = chosen.inflect({"datv"})
        if inflected is None:
            return word

        result = inflected.word
        if word[0].isupper():
            result = result[0].upper() + result[1:]
        return result
    except Exception as e:
        log.warning("Не удалось склонить слово (дательный) %r: %s", word, e)
        return word


def decline_fio(fio: str) -> str:
    """Склоняет ФИО в родительный падеж.

    При неудаче возвращает вход без изменений.
    """
    raw = (fio or "").strip()
    if not raw:
        return raw

    if not _PYMORPHY_AVAILABLE:
        return raw

    if not _CYRILLIC_RE.match(raw):
        return raw

    parts = raw.split()
    if len(parts) != 3:
        return raw

    try:
        last_raw, first_raw, middle_raw = parts
        gender = _detect_gender(middle_raw)

        last = _inflect_genitive(last_raw, kind="Surn", gender=gender)
        first = _inflect_genitive(first_raw, kind="Name", gender=gender)
        middle = _inflect_genitive(middle_raw, kind="Patr", gender=gender)

        return f"{last} {first} {middle}"
    except Exception as e:
        log.warning("Не удалось склонить ФИО %r: %s", raw, e)
        return raw