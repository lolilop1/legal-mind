"""Legal Trace — цепочка «Факт → Квалификация → Норма → Источник».

Показывает пользователю, как система пришла к конкретной норме.
Не заменяет hard-check, а дополняет его — объясняет что понял код.

Используется в карточке дела /case/... и (опционально) в PDF.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


# ─── Квалификации для каждого модуля ───
QUALIFICATIONS = {
    "uk": "ненадлежащее содержание общего имущества многоквартирного дома",
    "noise": "нарушение тишины и покоя граждан",
    "consumer": "нарушение прав потребителя",
}

# ─── Источники (для модуля 2 — федеральные, для модуля 3 — из БД) ───
FEDERAL_SOURCES = {
    "uk": "Федеральное законодательство РФ · consultant.ru",
}


@dataclass
class TraceStep:
    label: str
    value: str


@dataclass
class LegalTrace:
    fact: str = ""
    qualification: str = ""
    norms: list[str] = field(default_factory=list)
    source: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def is_empty(self) -> bool:
        # Пустой trace — когда нет ни факта, ни норм.
        # qualification — метаданные, подставляются всегда.
        return not (self.fact or self.norms)


def build_trace(
    problem_type: str,
    problem_text: str,
    norms: list[str] | None = None,
    source: str = "",
    qualification: str = "",
) -> LegalTrace:
    """Собирает цепочку «Факт → Квалификация → Норма → Источник».

    Args:
        problem_type: uk / noise / consumer
        problem_text: текст пользователя (обрежется до 120 символов)
        norms: список норм (для модуля 2 — из ALLOWED_UK_NORMS, для модуля 3 — закон)
        source: URL источника (для модуля 3 — из law_data)
        qualification: переопределить квалификацию (иначе из QUALIFICATIONS)

    Returns:
        LegalTrace с заполненными полями.
    """
    fact = (problem_text or "").strip()
    # Обрезаем до 120 символов, добавляем многоточие
    if len(fact) > 120:
        fact = fact[:117] + "..."

    qual = qualification or QUALIFICATIONS.get(problem_type, "юридически значимое действие")

    src = source or FEDERAL_SOURCES.get(problem_type, "")

    norms_list = list(norms) if norms else []

    return LegalTrace(
        fact=fact,
        qualification=qual,
        norms=norms_list,
        source=src,
    )