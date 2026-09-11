"""Legal Mind — Module 3: neighbor noise complaint hard checks.

v3.1:
- Alphabet check: reject emoji-only, digits-only, punctuation-only input.
"""

from __future__ import annotations

import re
from typing import Optional


EMERGENCY_PATTERNS = (
    r"угрожа(?:ет|ют|л|ла|ли)\s+(?:убить|расправ|физической|расправой)",
    r"угрожа(?:ет|ют|л|ла|ли)\s+(?:мне|нам|семье|детям)",
    r"убива(?:ет|ют|л|ла|ли)",
    r"напада(?:ет|ют|л|ла|ли)",
    r"лома(?:ет|ют|л|ла|ли)\s+двер",
    r"выбива(?:ет|ют|л|ла|ли)\s+двер",
    r"с\s+ножом",
    r"с\s+топором",
    r"с\s+оружием",
    r"избива(?:ет|ют|л|ла|ли)",
    r"драк[аиу]\b",
    r"порезал|ранил",
)
_EMERGENCY_RE = tuple(re.compile(p, re.IGNORECASE) for p in EMERGENCY_PATTERNS)


NOISE_MARKERS = (
    "шум", "шумн", "шумят", "шумит",
    "громк", "громко",
    "музык",
    "крич", "крики", "орут", "орет",
    "топот", "топают", "топает",
    "сверл", "сверлят", "сверлит",
    "долб", "долбят", "долбит",
    "ремонт",
    "пианин", "гитар", "барабан", "музыкальный инструмент",
    "лай", "лает", "собака лает", "собаки лают", "воют",
    "пьян", "дебош", "скандал",
    "пляс", "танц", "вечеринк", "гулянк",
    "не дают спать", "невозможно спать", "не могу спать",
    "нарушают тишину",
)
_NOISE_RE = re.compile("|".join(re.escape(m) for m in NOISE_MARKERS), re.IGNORECASE)


_NEIGHBOR_RE = re.compile(
    r"(?:"
    r"сосед|соседк|соседск|"
    r"сверху|снизу|"
    r"за\s+стен(?:ой|кой|ами)|"
    r"из\s+квартиры|"
    r"в\s+квартире\s+(?:выше|ниже|рядом)|"
    r"кв\.?\s*\d+|"
    r"этажом\s+(?:выше|ниже)|"
    r"напротив"
    r")",
    re.IGNORECASE,
)


_ALPHABET_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")


def _normalize(text: object) -> str:
    s = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    s = re.sub(r"\bкв\.", "кв", s)
    return s


def _stop(emergency: bool, reason: str) -> dict:
    return {
        "stop": True,
        "emergency": emergency,
        "stop_reason": reason,
        "описание_проблемы_формальное": None,
        "применимая_норма": None,
    }


def emergency_signal(text: str) -> Optional[str]:
    s = _normalize(text)
    if not s:
        return None
    for pattern in _EMERGENCY_RE:
        m = pattern.search(s)
        if m:
            return m.group(0)
    return None


def noise_signal(text: str) -> bool:
    return bool(_NOISE_RE.search(_normalize(text)))


def neighbor_signal(text: str) -> bool:
    return bool(_NEIGHBOR_RE.search(_normalize(text)))


def hard_pre_check(user_data: dict) -> Optional[dict]:
    problem = _normalize(user_data.get("проблема", ""))

    emergency = emergency_signal(problem)
    if emergency:
        return _stop(
            True,
            "Это похоже на прямую угрозу жизни или здоровью. "
            "Не тратьте время на заявление — звоните 112 немедленно. "
            "После того как ситуация разрешится, заявление участковому "
            "можно будет подать для фиксации нарушения и привлечения "
            "виновных к ответственности.",
        )

    if len(problem) < 10:
        return _stop(
            False,
            "Описание проблемы слишком короткое — уточните, что именно происходит.",
        )

    if not _ALPHABET_RE.search(problem):
        return _stop(
            False,
            "Описание проблемы не содержит текста — опишите проблему словами.",
        )

    if not noise_signal(problem):
        return _stop(
            False,
            "Не похоже на жалобу о шуме или нарушении тишины. Уточните, "
            "что именно происходит: громкая музыка, ремонт, крики, "
            "лай собаки или другое.",
        )

    if not neighbor_signal(problem):
        return _stop(
            False,
            "Из описания не ясно, кто именно создаёт шум — сосед, "
            "квартира сверху, за стеной. Уточните источник шума.",
        )

    if not str(user_data.get("адрес", "") or "").strip():
        return _stop(
            False,
            "Не указан адрес — без него заявление участковому "
            "составить невозможно.",
        )

    return None