"""Legal Mind — Module 1: PDF generation for consumer complaints.

Формат: претензия продавцу/исполнителю по ЗоЗПП.

Структура:
- Шапка: «Директору {продавец}, Адрес: {адрес_продавца}»
         + блок «от гр. ФИО, адрес, телефон»
- Заголовок: ПРЕТЕНЗИЯ + юридически корректный подзаголовок
- Тело: описание + нормы
- Блок ТРЕБУЮ: пункты + срок из конфига
- Предупреждение о суде
- Дата, подпись, подвал с версиями
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


# Юридически корректные подзаголовки по сценариям
_SUBTITLES = {
    "defect":      "о возврате стоимости товара ненадлежащего качества",
    "return14":    "о возврате товара надлежащего качества",
    "marketplace": "о нарушении прав потребителя при дистанционной покупке",
    "service":     "о некачественном оказании услуг",
}


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
    """Рендерит PDF-претензию по ЗоЗПП.

    requisites keys: продавец, адрес_продавца, фио, адрес, телефон
    normalized keys: описание_проблемы_формальное, требование,
                     применимые_нормы (list[str]),
                     engine_version, rules_date, template_version
    config (опционально): конфиг сценария для подзаголовка и сроков.
    """
    family, regular_path, bold_path = _find_font_pair()

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(left=20, top=15, right=15)
    pdf.add_page()

    pdf.add_font(family, style="", fname=regular_path)
    pdf.add_font(family, style="B", fname=bold_path)

    seller = requisites.get("продавец") or "Продавец (наименование не указано)"
    seller_address = requisites.get("адрес_продавца") or "[адрес уточняется]"

    # Формы по полу (определяется в app.py через detect_gender)
    _pol = (requisites.get("пол") or "masc").lower()
    F_PROZHIV = "проживающей" if _pol == "femn" else "проживающего"
    F_VYN = "вынуждена" if _pol == "femn" else "вынужден"

    # ─── Header: Директору + адрес продавца + блок потребителя ───
    header_text = (
        f"Директору {seller}\n"
        f"Адрес: {seller_address}\n"
        f"\n"
        f"от гр. {requisites['фио']}\n"
        f"{F_PROZHIV} по адресу:\n"
        f"{requisites['адрес']}\n"
        f"контактный телефон: {requisites['телефон']}"
    )
    pdf.set_font(family, style="", size=11)
    _mc(pdf, 5.5, header_text, align="R")

    # ─── Title ───
    pdf.ln(12)
    pdf.set_font(family, style="B", size=14)
    _mc(pdf, 7, "ПРЕТЕНЗИЯ", align="C")

    subtitle = _SUBTITLES.get(
        config["code"] if config else "",
        "о нарушении прав потребителя",
    )
    pdf.set_font(family, style="", size=11)
    _mc(pdf, 5.5, subtitle, align="C")
    pdf.ln(6)

    # ─── Body ───
    pdf.set_font(family, style="", size=11)
    _mc(pdf, 5.5, "    " + normalized["описание_проблемы_формальное"], align="J")

    pdf.ln(4)
    _mc(pdf, 5.5, "Указанное нарушение противоречит требованиям:", align="J")

    norms = normalized.get("применимые_нормы") or []
    for i, norm in enumerate(norms, start=1):
        _mc(pdf, 5.5, f"    {i}. {norm}.", align="J")

    pdf.ln(4)
    _mc(pdf, 5.5, "На основании изложенного,", align="J")

    # ─── ТРЕБУЮ ───
    pdf.ln(3)
    pdf.set_font(family, style="B", size=11)
    _mc(pdf, 6, "ТРЕБУЮ:", align="L")
    pdf.set_font(family, style="", size=11)

    demand = (normalized.get("требование") or "").strip()
    if not demand:
        demand = "удовлетворить мои законные требования как потребителя"

    # Пункт 1 — требование потребителя
    _mc(pdf, 5.5, f"    1. {demand[0].upper() + demand[1:]}.", align="J")
    pdf.ln(1)

    # Пункт 2 — срок из конфига (если нашли совпадение)
    if config:
        # Ищем по ЛЮБОМУ слову из wording, а не только по первому
        primary_demand = None
        demand_lower = demand.lower()
        for d in config.get("demand_options", []):
            # Разбиваем wording на слова, ищем пересечение
            words = [w.lower().strip(",.") for w in d["wording"].split() if len(w) > 4]
            if any(w in demand_lower for w in words):
                primary_demand = d
                break
        # Если не нашли по словам — берём первый по умолчанию
        if not primary_demand and config.get("demand_options"):
            primary_demand = config["demand_options"][0]

        if primary_demand and primary_demand.get("deadline_days"):
            deadline = primary_demand["deadline_days"]
            legal = primary_demand.get("deadline_legal", "")
            legal_part = f" ({legal})" if legal else ""
            _mc(
                pdf, 5.5,
                f"    2. Удовлетворить требование в течение {deadline} "
                f"календарных дней{legal_part} с момента получения "
                f"настоящей претензии.",
                align="J",
            )
            pdf.ln(1)

    # Пункт 3 — ответ в письменной форме
    _mc(
        pdf, 5.5,
        "    3. О принятом решении сообщить мне в письменной форме "
        "по адресу, указанному в шапке настоящей претензии.",
        align="J",
    )

    # ─── Предупреждение ───
    pdf.ln(4)
    _mc(
        pdf, 5.5,
        "В случае неудовлетворения претензии в установленный срок "
        f"я буду {F_VYN} обратиться в суд с требованием о защите "
        "прав потребителя, включая взыскание неустойки, компенсации "
        "морального вреда и штрафа в соответствии с действующим "
        "законодательством.",
        align="J",
    )

    # ─── Date + signature ───
    pdf.ln(15)
    today = date.today()
    date_str = f"{today.day:02d}.{today.month:02d}.{today.year}"
    _mc(pdf, 6, f"Дата: {date_str}", align="L")
    pdf.ln(2)
    _mc(pdf, 6, "Подпись: ___________________", align="L")

    # ─── Подвал ───
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