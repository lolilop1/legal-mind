"""Legal Mind — Module 3: PDF generation for noise complaints.

v3: uses list format for the legal reference (aligned with module 2).
"""

from __future__ import annotations

import os
from datetime import date

from fpdf import FPDF


_FONT_CANDIDATES = [
    ("DejaVu",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("Arial",
     "C:/Windows/Fonts/arial.ttf",
     "C:/Windows/Fonts/arialbd.ttf"),
    ("Arial",
     "/Library/Fonts/Arial.ttf",
     "/Library/Fonts/Arial Bold.ttf"),
    ("Liberation",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
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
    pdf.multi_cell(0, height, text, align=align)
    pdf.set_x(pdf.l_margin)


def generate_pdf(output_path: str, requisites: dict, normalized: dict) -> str:
    family, regular_path, bold_path = _find_font_pair()

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(left=20, top=15, right=15)
    pdf.add_page()

    pdf.add_font(family, style="", fname=regular_path)
    pdf.add_font(family, style="B", fname=bold_path)

    # ─── Header ───
    header_text = (
        f"{requisites['адресат']}\n"
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
    _mc(pdf, 7, "ЗАЯВЛЕНИЕ", align="C")

    pdf.set_font(family, style="", size=11)
    _mc(pdf, 5.5, "о нарушении тишины и покоя граждан", align="C")
    pdf.ln(6)

    # ─── Body ───
    pdf.set_font(family, style="", size=11)
    _mc(pdf, 5.5, "    " + normalized["описание_проблемы_формальное"], align="J")

    pdf.ln(4)

    # ─── Правовая ссылка ───
    law = (normalized.get("применимая_норма") or "").strip()
    if law:
        _mc(
            pdf,
            5.5,
            "Указанные действия нарушают требования:",
            align="J",
        )
        _mc(pdf, 5.5, f"    1. {law}.", align="J")
    else:
        _mc(
            pdf,
            5.5,
            "Указанные действия содержат признаки административного "
            "правонарушения, посягающего на тишину и покой граждан.",
            align="J",
        )

    pdf.ln(4)
    _mc(pdf, 5.5, "На основании изложенного,", align="J")

    pdf.ln(3)
    pdf.set_font(family, style="B", size=11)
    _mc(pdf, 6, "ПРОШУ:", align="L")

    pdf.set_font(family, style="", size=11)
    request_items = [
        "1. Провести проверку по факту изложенного нарушения.",
        "2. Привлечь виновных лиц к ответственности в соответствии "
        "с законодательством Российской Федерации об административных "
        "правонарушениях.",
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