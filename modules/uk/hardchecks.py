"""Legal Mind — Module 2 deterministic hard checks.

v2.4:
- Reordered: neighbor routing before vague-object check.
- Vague-object check skipped when any emergency keyword present.
"""

from __future__ import annotations

import re
from typing import Optional


EMERGENCY_KEYWORDS = (
    "запах газа", "пахнет газом", "пахло газом", "утечка газа",
    "воняет газом", "вонь газа", "тянет газом",
    "трещина в несущей", "трещина в стене", "обрушение", "обрушается",
    "обрушивается потолок", "обрушился потолок",
    "пожар", "горит", "загорелось",
    "искрит проводка", "искрила проводка", "короткое замыкание", "искрит розетка",
    "прорвало трубу", "затапливает подъезд", "провалился потолок",
)


_NEIGHBOR_NOUN = (
    r"(?:"
    r"сосед(?:а|у|ом|е|и|ей|ям|ями|ях|ка|ки|ке|ку|кой|ок|кам|ками|ках)?"
    r"|(?:из\s+)?(?:квартиры|квартира|кв)\s*№?\s*\d+"
    r"|квартира\s+(?:моего|моей|своего|соседа|соседки|соседей)"
    r")"
)

_NEIGHBOR_BEHAVIOR = (
    r"(?:"
    r"шум(?:ит|ят|ел|ели|но)?" r"|"
    r"громк(?:ий|ая|ое|ие|о)" r"|"
    r"музык(?:а|у|ой|е)" r"|"
    r"крич(?:ит|ат|ал|али)?" r"|"
    r"кур(?:ит|ят|ил|или)?" r"|"
    r"меша(?:ет|ют|л|ли)?" r"|"
    r"ремонт(?:ируют|ировался|ировались|ирует)?" r"|"
    r"сверл(?:ит|ят|ил|или)?" r"|"
    r"долб(?:ит|ят|ил|или)?" r"|"
    r"грохоч(?:ет|ут)?" r"|"
    r"топ(?:от|аю|ает|ают|ал|ала|али)?" r"|"
    r"дебошир(?:ит|ят|ил|или)?" r"|"
    r"скандал(?:ит|ят|ил|или)?" r"|"
    r"источник[^.!?;\n]{0,30}шума" r"|"
    r"не\s+дают\s+спать" r"|"
    r"нарушают\s+тишину" r"|"
    r"устраивают\s+шум"
    r")"
)

_NEIGHBOR_FORWARD = re.compile(
    rf"\b{_NEIGHBOR_NOUN}\b[^.!?;\n]{{0,100}}\b{_NEIGHBOR_BEHAVIOR}\b",
    re.IGNORECASE,
)
_NEIGHBOR_REVERSE = re.compile(
    rf"\b{_NEIGHBOR_BEHAVIOR}\b[^.!?;\n]{{0,100}}\b{_NEIGHBOR_NOUN}\b",
    re.IGNORECASE,
)


_RESOLVED_PATTERNS = (
    r"сейчас\s+(?:всё\s+)?(?:нормально|безопасно|тихо)",
    r"сейчас\s+(?:запаха|запах)\s+(?:газа\s+)?нет",
    r"запаха\s+газа\s+нет",
    r"запах\s+газа\s+(?:исчез|пропал|пропал[оа]|устранён|устранен)",
    r"утечк[аи]\s+газа\s+(?:устранена|устранено|устранён|устранен)",
    r"утечк[аи]\s+газа\s+(?:нет|больше\s+нет)",
    r"(?:утечка\s+газа|пожар|искрила\s+проводка)[^.!?;\n]{0,100}"
    r"(?:устранен|устранена|устранено|потушен|потушена|потушили|погасили|"
    r"ликвидирован|ликвидирована|исчез|исчезла|нет|нормально|безопасно)",
    r"пожар\s+(?:потушен|ликвидирован)",
    r"пожар[^.!?;\n]{0,40}(?:потушили|погасили|ликвидировали)",
    r"проводк[аи]\s+(?:больше\s+не\s+искрит|перестала\s+искрить)",
    r"искрение\s+(?:устранено|прекратилось)",
    r"трещин[аы]\s+больше\s+не\s+(?:увеличивается|расширяется)",
)
_RESOLVED_RE = tuple(re.compile(p, re.IGNORECASE) for p in _RESOLVED_PATTERNS)


_HISTORICAL_PATTERNS = (
    r"(?:вчера|позавчера|накануне|раньше|тогда|недавно|"
    r"на\s+прошлой\s+неделе|в\s+прошлом\s+месяце|"
    r"пару\s+дней\s+назад|несколько\s+дней\s+назад|несколько\s+часов\s+назад|"
    r"на\s+днях)\b[^.!?;\n]{0,120}\b"
    r"(?:пахло\s+газом|воняло\s+газом|был(?:а|о)?\s+утечка\s+газа|"
    r"искрила\s+проводка|был(?:а|о)?\s+пожар|загорелось)",
    r"\bпожар\b[^.!?;\n]{0,40}\b(?:вчера|позавчера|накануне|раньше|недавно)\b",
    r"\b(?:вчера|позавчера|накануне|раньше|недавно)\b[^.!?;\n]{0,60}\b"
    r"(?:горел|горела|горело|дымил|дымила|искрил|искрила|искрило)\b",
)
_HISTORICAL_RE = tuple(re.compile(p, re.IGNORECASE) for p in _HISTORICAL_PATTERNS)


_CURRENT_EMERGENCY_PATTERNS = (
    r"\bсейчас\b[^.!?;\n]{0,50}\b"
    r"(?:пахнет\s+газом|воняет\s+газом|есть\s+запах\s+газа|"
    r"снова\s+пахнет\s+газом|опять\s+пахнет\s+газом|"
    r"снова\s+воняет\s+газом|опять\s+воняет\s+газом|"
    r"искрит|горит|дымит)\b",
    r"\b(?:снова|опять)\b[^.!?;\n]{0,40}\b"
    r"(?:пахнет\s+газом|воняет\s+газом|есть\s+запах\s+газа|"
    r"запах\s+газа|тянет\s+газом)\b",
    r"\bпрямо\s+сейчас\b[^.!?;\n]{0,50}\b"
    r"(?:пахнет\s+газом|воняет|искрит|горит|дым)\b",
    r"\bв\s+данный\s+момент\b[^.!?;\n]{0,50}\b"
    r"(?:пахнет\s+газом|воняет|искрит|горит|дым)\b",
    r"\bзапах\s+газа\b[^.!?;\n]{0,50}\b"
    r"(?:не\s+проходит|не\s+исчезает|сохраняется)\b",
    r"\bутечка\s+газа\b[^.!?;\n]{0,50}\b"
    r"(?:продолжается|не\s+устранена|есть)\b",
)
_CURRENT_RE = tuple(re.compile(p, re.IGNORECASE) for p in _CURRENT_EMERGENCY_PATTERNS)


_ONGOING_PATTERNS = (
    r"до\s+сих\s+пор",
    r"до\s+сегодняшнего\s+дня",
    r"всё\s+ещё",
    r"все\s+еще",
    r"не\s+устранен(?:а|о|ы)?",
    r"не\s+устранили",
    r"не\s+починили",
    r"не\s+исправили",
    r"продолжается",
    r"сохраняется",
    r"не\s+прекращается",
    r"не\s+проходит",
)
_ONGOING_RE = tuple(re.compile(p, re.IGNORECASE) for p in _ONGOING_PATTERNS)


_ALPHABET_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")


_SPECIFIC_OBJECT_MARKERS = (
    "убир", "мусор", "гряз", "снег", "налед", "гололёд", "гололед", "сосульк",
    "лифт",
    "крыш", "кровл", "протечк", "потолок", "течёт", "течет", "подтоплен", "залив",
    "домофон", "двер", "калитк", "ворота",
    "проводк", "электр", "свет", "лампочк", "освещен", "розетк",
    "батаре", "отоплен", "радиатор", "тепл", "холодн", "мерзн", "мерзл",
    "вод", "канализац", "труб", "кран", "унитаз", "смесител",
    "стен", "фасад", "штукатурк", "плитк", "трещин",
    "подъезд", "подвал", "чердак", "лестниц", "перил", "ступен",
    "окн", "стекл", "рам", "балкон",
    "газ",
    "двор", "территор", "площадк", "парковк", "тротуар", "газон",
    "вент", "вытяжк", "душно", "духота",
    "запах", "воня", "сыро", "плесен", "гриб",
    "насеком", "таракан", "мыш", "крыс", "комары",
    "ламп", "светильник",
)
_SPECIFIC_RE = re.compile("|".join(re.escape(m) for m in _SPECIFIC_OBJECT_MARKERS), re.IGNORECASE)


_VAGUE_THRESHOLD = 150


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


def _matched_emergency_phrase(s: str) -> str:
    for phrase in EMERGENCY_KEYWORDS:
        if phrase in s:
            return phrase
    return "текущая аварийная ситуация"


def _has_any_emergency_keyword(s: str) -> bool:
    return any(kw in s for kw in EMERGENCY_KEYWORDS)


def emergency_signal(text: str) -> Optional[str]:
    s = _normalize(text)
    if not s:
        return None

    for pattern in _CURRENT_RE:
        if pattern.search(s):
            return _matched_emergency_phrase(s)

    has_resolved = any(p.search(s) for p in _RESOLVED_RE)
    has_historical = any(p.search(s) for p in _HISTORICAL_RE)
    has_ongoing = any(p.search(s) for p in _ONGOING_RE)

    if has_ongoing:
        for phrase in EMERGENCY_KEYWORDS:
            if phrase in s:
                return phrase
        return None

    if has_resolved or has_historical:
        return None

    for phrase in EMERGENCY_KEYWORDS:
        if phrase in s:
            return phrase

    return None


def neighbor_behavior_signal(text: str) -> bool:
    s = _normalize(text)
    if not s:
        return False
    return bool(_NEIGHBOR_FORWARD.search(s) or _NEIGHBOR_REVERSE.search(s))


def specific_object_signal(text: str) -> bool:
    return bool(_SPECIFIC_RE.search(_normalize(text)))


def hard_pre_check(user_data: dict) -> Optional[dict]:
    problem = _normalize(user_data.get("проблема", ""))

    # 1. Emergency.
    emergency = emergency_signal(problem)
    if emergency:
        return _stop(
            True,
            "Это похоже на угрозу жизни или имуществу прямо сейчас. "
            "Не теряйте время на документ — звоните 112 (единая служба "
            "экстренных вызовов) или в аварийную службу УК немедленно. "
            "Жалобу на бездействие можно будет составить уже после того, "
            "как опасная ситуация устранена.",
        )

    # 2. Too short.
    if len(problem) < 10:
        return _stop(
            False,
            "Описание проблемы слишком короткое — уточните, что именно происходит.",
        )

    # 3. Alphabet check.
    if not _ALPHABET_RE.search(problem):
        return _stop(
            False,
            "Описание проблемы не содержит текста — опишите проблему словами.",
        )

    # 4. Neighbor routing — before vague check.
    if neighbor_behavior_signal(problem):
        return _stop(
            False,
            "Похоже, речь о поведении конкретных соседей, а не о содержании "
            "общего имущества дома. Для этого случая нужен другой модуль — "
            "«Жалоба на нарушение тишины».",
        )

    # 5. Vague-object check. Пропускаем если есть emergency-ключевик
    #    (например, "пожар был вчера, потушили") или длинное описание.
    if (len(problem) < _VAGUE_THRESHOLD
            and not _has_any_emergency_keyword(problem)
            and not specific_object_signal(problem)):
        return _stop(
            False,
            "Описание слишком общее — не ясно, что именно не работает. "
            "Уточните объект проблемы: уборка подъезда, отопление, лифт, "
            "крыша, домофон, проводка, вода, стены и т.п.",
        )

    # 6. Address.
    if not str(user_data.get("адрес", "") or "").strip():
        return _stop(
            False,
            "Не указан адрес — без него невозможно составить обращение в УК.",
        )

    return None