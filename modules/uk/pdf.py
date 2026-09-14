"""Legal Mind — Module 2: PDF generation (fpdf2 backend).

Uses fpdf2 instead of reportlab because fpdf2 embeds Unicode fonts with a
proper ToUnicode CMap, so text can be copied out of the resulting PDF.

Note on cursor handling: some fpdf2 versions leave the X cursor at the right
edge after a multi_cell with align="R" or "C". The next multi_cell(0, ...)
then sees zero available width and raises "Not enough horizontal space".
We defensively reset X to the left margin after every multi_cell.
"""

from __future__ import annotations

import os
from datetime import date

from fpdf import FPDF


_FONT_CANDIDATES = [
    (
        "DejaVu",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    (
        "Arial",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ),
    (
        "Arial",
        "/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ),
    (
        "Liberation",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ),
]


def _find_font_pair() -> tuple[str, str, str]:
    for family, regular, bold in _FONT_CANDIDATES:
        if os.path.exists(regular) and os.path.exists(bold):
            return family, regular, bold
    raise RuntimeError(
        "Не найден TTF-шрифт с поддержкой кириллицы. "
        "Установите Arial (Windows/macOS) или fonts-dejavu (Linux)."
    )


def _mc(pdf: FPDF, height: float, text: str, align: str = "L") -> None:
    """multi_cell + X-cursor reset. Always safe to chain."""
    pdf.multi_cell(0, height, text, align=align)
    pdf.set_x(pdf.l_margin)


def generate_pdf(output_path: str, requisites: dict, normalized: dict,
                 config: dict | None = None) -> str:
    """Render a PDF document.

    requisites keys: ук_название, фио, адрес, телефон.
    normalized keys: описание_проблемы_формальное,
                     упоминание_повторного_обращения,
                     применимые_нормы (list[str]).
    config (опционально): CONFIG документа (uk/gzhi/rpn/prokuratura/damage).
    """

    cfg = config or {}
    pdf_title = cfg.get("pdf_title", "ЗАЯВЛЕНИЕ")
    pdf_subtitle = cfg.get("pdf_subtitle",
                           "на ненадлежащее содержание общего имущества многоквартирного дома")
    pdf_request_block = cfg.get("pdf_request_block", "ПРОШУ:")
    family, regular_path, bold_path = _find_font_pair()

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(left=20, top=15, right=15)
    pdf.add_page()

    pdf.add_font(family, style="", fname=regular_path)
    pdf.add_font(family, style="B", fname=bold_path)

    # ─── Header ───
    header_text = (
        f"В {requisites['ук_название']}\n"
        f"от гр. {requisites['фио']}\n"
        f"проживающего(-ей) по адресу:\n"
        f"{requisites['адрес']}\n"
        f"контактный телефон: {requisites['телефон']}"
    )
    pdf.set_font(family, style="", size=11)
    _mc(pdf, 5.5, header_text, align="R")

    # ─── Title ───
    pdf.ln(12)
    pdf.set_font(family, style="B", size=14)
    _mc(pdf, 7, pdf_title, align="C")

    pdf.set_font(family, style="", size=11)
    _mc(
        pdf,
        5.5,
        pdf_subtitle,
        align="C",
    )
    pdf.ln(6)

    # ─── Body ───
    pdf.set_font(family, style="", size=11)
    _mc(pdf, 5.5, "    " + normalized["описание_проблемы_формальное"], align="J")

    repeat = (normalized.get("упоминание_повторного_обращения") or "").strip()
    if repeat:
        pdf.ln(3)
        _mc(pdf, 5.5, repeat, align="J")

    pdf.ln(4)
    _mc(
        pdf,
        5.5,
        "Указанное нарушение противоречит требованиям:",
        align="J",
    )

    norms = normalized.get("применимые_нормы") or []
    for i, norm in enumerate(norms, start=1):
        _mc(pdf, 5.5, f"    {i}. {norm}.", align="J")

    pdf.ln(4)
    _mc(pdf, 5.5, "На основании изложенного,", align="J")

    # ─── Proshu ───
    pdf.ln(3)
    pdf.set_font(family, style="B", size=11)
    _mc(pdf, 6, pdf_request_block, align="L")

    pdf.set_font(family, style="", size=11)
    request_items = [
        "1. Провести проверку по факту изложенного нарушения.",
        "2. Устранить выявленное нарушение в течение 10 (десяти) "
        "календарных дней с момента получения настоящего обращения.",
        "3. О результатах рассмотрения обращения сообщить мне в "
        "письменной форме по адресу проживания в установленный "
        "законом срок.",
    ]
    for item in request_items:
        _mc(pdf, 5.5, "    " + item, align="J")
        pdf.ln(1)

    # ─── Date + signature ───
    pdf.ln(15)
    today = date.today()
    date_str = f"{today.day:02d}.{today.month:02d}.{today.year}"
    _mc(pdf, 6, f"Дата: {date_str}", align="L")
    pdf.ln(2)
    _mc(pdf, 6, "Подпись: ___________________", align="L")

    # --- Подвал с версией документа ---
    engine = (normalized.get("engine_version") or "").strip()
    rules = (normalized.get("rules_date") or "").strip()
    template = (normalized.get("template_version") or "").strip()
    if engine or rules or template:
        pdf.ln(10)
        pdf.set_font(family, style="", size=8)
        parts = []
        if engine:
            parts.append(f"движок {engine}")
        if rules:
            parts.append(f"правила {rules}")
        if template:
            parts.append(f"шаблон {template}")
        footer = "Сгенерировано алгоритмом Legal Mind · " + " · ".join(parts)
        pdf.set_text_color(120, 120, 120)
        _mc(pdf, 4, footer, align="L")
        pdf.set_text_color(0, 0, 0)

    pdf.output(output_path)
    return output_path