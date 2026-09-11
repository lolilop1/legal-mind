"""Универсальные pre-checks: что знаем / чего не хватает.

Запускается ПОСЛЕ hard-check, но ДО LLM.
Цель: понять юридическую готовность CASE.

Если критичное отсутствует -> DOCUMENT BLOCKED.
Если опциональное -> отмечаем, но продолжаем.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CheckItem:
    label: str
    value: str | None = None
    hint: str | None = None


@dataclass
class PreCheckReport:
    known: list[CheckItem] = field(default_factory=list)
    missing_critical: list[CheckItem] = field(default_factory=list)
    missing_optional: list[CheckItem] = field(default_factory=list)

    @property
    def is_blocked(self) -> bool:
        return bool(self.missing_critical)

    def to_dict(self) -> dict:
        return {
            "known": [{"label": c.label, "value": c.value} for c in self.known],
            "missing_critical": [
                {"label": c.label, "hint": c.hint} for c in self.missing_critical
            ],
            "missing_optional": [
                {"label": c.label, "hint": c.hint} for c in self.missing_optional
            ],
            "is_blocked": self.is_blocked,
        }


def add_known(report: PreCheckReport, label: str, value: str | None) -> None:
    if value:
        report.known.append(CheckItem(label=label, value=str(value)))


def add_missing_critical(report: PreCheckReport, label: str, hint: str) -> None:
    report.missing_critical.append(CheckItem(label=label, hint=hint))


def add_missing_optional(report: PreCheckReport, label: str, hint: str) -> None:
    report.missing_optional.append(CheckItem(label=label, hint=hint))