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
import re
from datetime import date

from fpdf import FPDF

from modules.consumer.marketplaces import resolve_marketplace
from modules.consumer.categories import get_category
from core.name_declension import decline_fio_dative, detect_gender_by_name, _detect_gender


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


def _fmt_rub(value: float) -> str:
    """12345.67 -> '12 345,67'."""
    if value is None:
        return "—"
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def _mc(pdf: FPDF, height: float, text: str, align: str = "L") -> None:
    """multi_cell + X-cursor reset. Always safe to chain."""
    pdf.multi_cell(0, height, text, align=align)
    pdf.set_x(pdf.l_margin)


_JURIDICAL_PREFIXES = ("ООО", "АО", "ПАО", "ЗАО", "ОАО", "НКО",
                       "МУП", "ГУП", "ТСЖ", "ТД", "ТЦ")


def _decline_word(word: str, kind: str, gender: str | None = None) -> str:
    """Склоняет одно слово в дательный. Fallback — как есть."""
    from core.name_declension import _inflect_dative, _PYMORPHY_AVAILABLE
    if not _PYMORPHY_AVAILABLE:
        return word
    return _inflect_dative(word, kind=kind, gender=gender)


def _get_name_role(word: str) -> str | None:
    """Возвращает роль слова: 'Surn' / 'Name' / 'Patr' / None.

    Проверяет ТОЛЬКО именительный падеж единственного числа (sing,nomn).
    Так отличаем "Магазин" (обычное сущ.) от "Мария" (имя).
    """
    from core.name_declension import _MORPH, _PYMORPHY_AVAILABLE
    if not _PYMORPHY_AVAILABLE or not word:
        return None

    try:
        variants = _MORPH.parse(word)
        for v in variants:
            tag = v.tag
            if "sing" not in tag or "nomn" not in tag:
                continue
            if "Surn" in tag:
                return "Surn"
            if "Name" in tag:
                return "Name"
            if "Patr" in tag:
                return "Patr"
    except Exception:
        pass
    return None


def _format_addressee(seller: str) -> str:
    """Возвращает «кому адресуем» для шапки претензии."""
    s = (seller or "").strip()
    if not s:
        return "Директору"

    # Маркетплейс: адресуем владельцу агрегатора
    mp = resolve_marketplace(s)
    if mp:
        return f"Владельцу агрегатора {mp['entity']} ({mp['brand']})"

    upper = s.upper()

    for prefix in _JURIDICAL_PREFIXES:
        if upper.startswith(prefix + " ") or upper.startswith(prefix + "."):
            rest = s[len(prefix):].lstrip(" .").strip()
            if rest:
                first_ch = rest[0]
                if first_ch not in ("«", chr(0x201c), chr(34)):
                    rest = rest.strip("«»" + chr(0x201c) + chr(0x201d) + chr(34)).strip()
                    rest = "«" + rest + "»"
                return f"Директору {prefix} {rest}"
            return f"Директору {prefix}"

    if upper.startswith("ИП ") or upper.startswith("ИП."):
        return s

    if "самозанят" in s.lower():
        return s

    parts = s.split()

    # ─── 3 слова: Ф И О ───
    if len(parts) == 3:
        roles = [_get_name_role(p) for p in parts]
        if roles == ["Surn", "Name", "Patr"]:
            gender = detect_gender_by_name(parts[1]) or _detect_gender(parts[2])
            declined = decline_fio_dative(s)
            prefix = "Гражданке" if gender == "femn" else "Гражданину"
            return f"{prefix} {declined}"

    # ─── 2 слова: Ф И или И Ф ───
    if len(parts) == 2:
        role_a = _get_name_role(parts[0])
        role_b = _get_name_role(parts[1])

        if role_a == "Surn" and role_b == "Name":
            surname, name = parts[0], parts[1]
        elif role_a == "Name" and role_b == "Surn":
            name, surname = parts[0], parts[1]
        else:
            return f"Продавцу {s}"

        gender = detect_gender_by_name(name)
        if not gender:
            return f"Продавцу {s}"

        declined_surname = _decline_word(surname, "Surn", gender)
        declined_name = _decline_word(name, "Name", gender)
        prefix = "Гражданке" if gender == "femn" else "Гражданину"
        return f"{prefix} {declined_surname} {declined_name}"

    # ─── 1 слово: русское имя ───
    if len(parts) == 1:
        role = _get_name_role(s)
        if role != "Name":
            return f"Продавцу {s}"
        gender = detect_gender_by_name(s)
        if not gender:
            return f"Продавцу {s}"
        declined = _decline_word(s, "Name", gender)
        prefix = "Гражданке" if gender == "femn" else "Гражданину"
        return f"{prefix} {declined}"

    # Всё остальное — ник, ссылка, много слов, мусор
    return f"Продавцу {s}"




def _decline_word(word: str, kind: str, gender: str | None = None) -> str:
    """Склоняет одно слово в дательный. Fallback — как есть."""
    from core.name_declension import _inflect_dative, _PYMORPHY_AVAILABLE
    if not _PYMORPHY_AVAILABLE:
        return word
    return _inflect_dative(word, kind=kind, gender=gender)


def generate_pdf(output_path: str, requisites: dict, normalized: dict,
                 config: dict | None = None,
                 category: str | None = None) -> str:
    """Рендерит PDF-претензию по ЗоЗПП.

    requisites keys: продавец, адрес_продавца, фио, адрес, телефон
    normalized keys: описание_проблемы_формальное, требование,
                     применимые_нормы (list[str]),
                     engine_version, rules_date, template_version
    config (опционально): конфиг сценария.
    category (опционально): код категории товара (напр. "smartphone").
    """
    family, regular_path, bold_path = _find_font_pair()

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(left=20, top=15, right=15)
    pdf.add_page()

    pdf.add_font(family, style="", fname=regular_path)
    pdf.add_font(family, style="B", fname=bold_path)

    seller = requisites.get("продавец") or "Продавец (наименование не указано)"
    seller_address = requisites.get("адрес_продавца") or "адрес не указан"
    seller_link = (requisites.get("ссылка_продавца") or "").strip()

    # Формы по полу (определяется в app.py через detect_gender)
    _pol = (requisites.get("пол") or "masc").lower()
    F_PROZHIV = "проживающей" if _pol == "femn" else "проживающего"
    F_VYN = "вынуждена" if _pol == "femn" else "вынужден"

    # ─── Header: Директору + адрес продавца + блок потребителя ───
    _link_line = f"Профиль: {seller_link}\n" if seller_link else ""
    _order = (requisites.get("номер_заказа") or "").strip()
    _order_line = f"Номер заказа: {_order}\n" if _order else ""
    header_text = (
        f"{_format_addressee(seller)}\n"
        f"Адрес: {seller_address}\n"
        f"{_link_line}"
        f"{_order_line}"
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
    # Подстановка категории: «о возврате стоимости смартфона»
    cat = get_category(category) if category else None
    if cat and config:
        code = config.get("code", "")
        cat_title = cat["title"]
        if code == "defect":
            subtitle = f"о возврате стоимости {cat_title} ненадлежащего качества"
        elif code == "return14":
            subtitle = f"о возврате {cat_title} надлежащего качества"
        elif code == "marketplace":
            subtitle = f"о нарушении прав потребителя при покупке {cat_title}"
        elif code == "service":
            subtitle = f"о некачественном оказании услуг ({cat_title})"
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
    pdf.ln(1)

    # Пункт 4 — компенсация морального вреда (ст. 15 ЗоЗПП)
    _mc(
        pdf, 5.5,
        "    4. Компенсировать моральный вред, причинённый нарушением "
        "моих прав как потребителя, в размере, определяемом судом "
        "(ст. 15 ЗоЗПП).",
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

    # ─── Расчёт неустойки (если есть) ───
    calc = normalized.get("расчёт")
    if calc:
        pdf.ln(6)
        pdf.set_font(family, style="B", size=11)
        _mc(pdf, 6, "РАСЧЁТ НЕУСТОЙКИ:", align="L")
        pdf.set_font(family, style="", size=11)

        base_fmt = _fmt_rub(calc["base_amount"])
        penalty_fmt = _fmt_rub(calc["penalty"])
        total_fmt = _fmt_rub(calc["total"])

        _mc(pdf, 5.5, f"    Сумма основного требования: {base_fmt} руб.", align="L")
        if calc.get("price_bumped"):
            orig_fmt = _fmt_rub(calc["original_price"])
            _mc(
                pdf, 5.5,
                f"    (расчёт по цене на день предъявления — {base_fmt} руб. "
                f"вместо {orig_fmt} руб. на день покупки, ст. 24 ЗоЗПП)",
                align="L",
            )
        _mc(
            pdf, 5.5,
            f"    Неустойка: {penalty_fmt} руб. "
            f"({calc['rate_percent']}% × {calc['days_overdue']} дн. просрочки)",
            align="L",
        )
        _mc(pdf, 5.5, f"    Итого к уплате: {total_fmt} руб.", align="L")
        _mc(pdf, 5.5, f"    Основание: {calc['law']}.", align="L")
        if calc.get("capped"):
            _mc(
                pdf, 5.5,
                "    (неустойка ограничена ценой услуги — п. 5 ст. 28 ЗоЗПП)",
                align="L",
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