"""Pre-checks для модуля 1 (Защита прав потребителя).

Что критично для претензии:
- товар/услуга (что куплено)
- суть проблемы (что не так)

Что опционально:
- дата покупки
- сумма
"""

from __future__ import annotations

import datetime as _dt
import re

from modules.consumer.marketplaces import resolve_marketplace

from core.pre_checks import (
    PreCheckReport,
    add_known,
    add_missing_critical,
    add_missing_optional,
)


# ─── Что куплено: товар или услуга ───
_ITEM_PATTERNS = [
    # Электроника (латиница + русские названия)
    (r"телефон|смартфон|мобил|мобильник|айфон|iphone|"
     r"samsung|самсунг|сяоми|xiaomi|хуавей|huawei|"
     r"оппо|oppo|виво|vivo|реалми|realme|"
     r"ноутбук|ноут|компьютер|планшет|макбук|macbook|"
     r"эпл|apple|mac\b|пк\b|моноблок",
     "Электроника / гаджет"),
    (r"холодильник|стиральн|посудомоечн|микроволнов|пылесос|кофемашин|"
     r"мультиварк|блендер|утюг|фен\b|электрочайник",
     "Бытовая техника"),
    (r"телевизор|монитор|наушник|колонк|саундбар|"
     r"проектор|ресивер",
     "Аудио/видео"),
    (r"куртк|пальто|плать|джинс|джинсы|обувь|ботинк|кроссовк|сапог|"
     r"футболк|рубашк|брюк|штан|костюм|свитер|свитшот|носк|бель",
     "Одежда / обувь"),
    (r"мебел|диван|кресл|стол|стул|шкаф|кроват|комод|тумб|полк",
     "Мебель"),
    (r"продукт|еда\b|еды\b|"
     r"молок|хлеб|мяс|рыб|сыр|колбас",
     "Продукты"),
    (r"медикам|лекарств|таблетк|мазь|крем|витамин",
     "Лекарства / медизделия"),
    (r"ремонт|отделк|стройматериал|обои|плитк|ламинат|линолеум|"
     r"краск|шпаклевк|гипсокартон",
     "Ремонт / строительство"),
    (r"доставк|курьер",
     "Доставка"),
    (r"курс|обучени|тренинг|вебинар|урок|лекц|мастер.?класс|вебинар",
     "Обучение / курсы"),
    (r"стрижк|маникюр|педикюр|косметолог|массаж|"
     r"наращиван|окрашиван|парикмахер",
     "Бытовые услуги"),
    (r"авиабилет|жд.?билет|путёвк|путевк|отел|гостиниц|тур|"
     r"круиз|экскурс",
     "Туризм / поездки"),
    (r"автомобил|машин|авто\b|мотоцикл|велосипед",
     "Автомобиль / транспорт"),
    (r"юридическ|юрист|адвокат|нотариус",
     "Юруслуги"),
]


# ─── Суть проблемы (все формы времени) ───
# Техсложные товары (Пост. 924) — для пометки в pre-check
_TECH_COMPLEX_PRE = re.compile(
    r"холодильник|морозильник|стиральн|посудомоечн|свч|микроволнов|"
    r"электроплит|электродуховк|кондиционер|водонагревател|"
    r"компьютер|ноутбук|моноблок|системн|монитор|клавиатур|"
    r"принтер|сканер|мфу|навигатор|"
    r"смартфон|телефон|айфон|iphone|samsung|сяоми|xiaomi|"
    r"телевизор|проектор|видеокамер|игров|playstation|xbox|"
    r"электронн\w*\s+книг|мебел|диван|шкаф|"
    r"газов\w*\s+котел|перфоратор|дрел|электроинструмент|радиостанц",
    re.IGNORECASE,
)


_PROBLEM_PATTERNS = [
    # Товар неисправен / брак (ловит корни, в т.ч. с опечатками типа "слмоался")
    (r"брак|дефект|слом|сломал|не работ|не работ|переста[л|ла|ли]|"
     r"переста|неисправн|не функцион|вышел из строя|вышла из строя|"
     r"не включ|не завод|поломал|слома|сломает|"
     r"день\s+прораб|прораб|не работ",
     "Товар неисправен / брак"),

    # Товар не подошёл
    (r"не подош|не подход|не тот размер|не тот цвет|не понравил|"
     r"не устроил|не подходят|маломерит|большемерит",
     "Товар не подошёл"),

    # Услуга некачественная
    (r"не оказал|не выполн|некачествен|недобросовестн|плохо сделал|халтур|"
     r"плохо выполн|испортил|плохо сдела",
     "Услуга оказана некачественно"),

    # Просрочка доставки
    (r"не доставил|не привезл|задержк достав|просрочк|"
     r"не пришл|задержал достав",
     "Нарушение срока доставки"),

    # Отказ продавца от требований (общий)
    (r"отказа|не принима|не вернул|не вернет|не хотят|не хочет|"
     r"не желает|не возвращ|не возврат",
     "Отказ продавца от требований"),
]


# ─── Дата покупки ───
_DATE_PATTERN = re.compile(
    r"\b\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}\b"
    r"|\bвчера\b|\bсегодня\b|\bпозавчера\b"
    r"|\bнедел[юи]\b|\bмесяц\b|\bполгода\b"
    r"|\b\d+\s+дн(?:я|ей|ь)\b",
    re.IGNORECASE,
)


def _parse_purchase_date(raw: str):
    """Парсит дату покупки из строки. Возвращает date или None."""
    if not raw:
        return None
    s = raw.strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d-%m-%Y", "%d-%m-%y",
                "%d/%m/%Y", "%d/%m/%y"):
        try:
            return _dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _match_first(text: str, patterns: list[tuple[str, str]]) -> str | None:
    for pattern, label in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return label
    return None


_PURCHASE_MARKERS = re.compile(
    r"\bкупил|\bкупила|\bприобр[её]л|\bприобр[её]ла|"
    r"\bзаказал|\bзаказала|\bоформил|\bоформила|"
    r"\bоплатил|\bоплатила",
    re.IGNORECASE,
)


def _has_purchase_marker(text: str) -> bool:
    """Есть ли явное указание на покупку: купил/приобрёл/заказал."""
    return bool(_PURCHASE_MARKERS.search(text))


from modules.consumer.marketplaces import MARKETPLACES as _MP_DICT

_KNOWN_MARKETPLACES_PRE = tuple(
    alias
    for data in _MP_DICT.values()
    for alias in data["aliases"]
)


_LEGAL_PREFIXES_PRE = ("ООО", "АО", "ПАО", "ЗАО", "ОАО", "НКО",
                        "МУП", "ГУП", "ТСЖ", "ТД", "ТЦ")


def _is_legal_entity_pre(seller: str) -> bool:
    """True если продавец похож на организацию, ИП или самозанятого."""
    s = (seller or "").strip()
    if not s:
        return True
    upper = s.upper()
    for prefix in _LEGAL_PREFIXES_PRE:
        if upper.startswith(prefix + " ") or upper.startswith(prefix + "."):
            return True
    if upper.startswith("ИП ") or upper.startswith("ИП."):
        return True
    if "самозанят" in s.lower():
        return True
    s_low = s.lower()
    if any(m in s_low for m in _KNOWN_MARKETPLACES_PRE):
        return True
    return False


def run_consumer_pre_checks(user_data: dict, extras: dict | None = None,
                             scenario: str | None = None) -> PreCheckReport:
    report = PreCheckReport()
    problem = (user_data.get("проблема") or "").strip()
    seller = (user_data.get("продавец") or "").strip()
    date_bought = (user_data.get("дата_покупки") or "").strip()

    # Known
    add_known(report, "Тип проблемы", "Защита прав потребителя")

    mp_data = resolve_marketplace(seller) if seller else None

    if not seller:
        add_missing_critical(
            report,
            "Продавец / исполнитель",
            "Не указано название магазина, компании или маркетплейса.",
        )
    elif mp_data:
        add_known(
            report,
            "Ответчик",
            f"{mp_data['brand']} — владелец агрегатора, "
            f"{mp_data['entity']}",
        )
    else:
        add_known(report, "Продавец / исполнитель", seller)

    # ─── Номер заказа для маркетплейса ───
    if mp_data:
        order = (user_data.get("номер_заказа") or "").strip()
        if order:
            add_known(report, "Номер заказа", order)
        else:
            add_missing_critical(
                report,
                "Номер заказа",
                f"Для претензии на маркетплейс {mp_data['brand']} "
                "номер заказа обязателен — без него агрегатор не "
                "идентифицирует сделку.",
            )

    seller_address = (user_data.get("адрес_продавца") or "").strip()
    seller_link = (user_data.get("ссылка_продавца") or "").strip()
    _is_legal = _is_legal_entity_pre(seller)

    if seller_address:
        add_known(report, "Адрес продавца", seller_address)
    elif seller_link:
        add_known(report, "Ссылка на профиль", seller_link)
    elif _is_legal:
        add_missing_critical(
            report,
            "Адрес продавца",
            "Для организации/ИП адрес обязателен — он есть в ЕГРЮЛ/ЕГРИП, "
            "в чеке или на сайте.",
        )
    else:
        # Физлицо без адреса и без ссылки — критично
        add_missing_critical(
            report,
            "Адрес или ссылка на продавца",
            "Для продавца-физлица нужен хотя бы один идентификатор: "
            "адрес или ссылка на профиль (Авито, Telegram, ВК).",
        )

    # Что куплено
    item = _match_first(problem, _ITEM_PATTERNS)
    if item:
        add_known(report, "Товар / услуга", item)
    elif _has_purchase_marker(problem) and len(problem) >= 30:
        # Категория не распозналась, но явно описан товар — не блокируем
        add_known(report, "Товар / услуга", "Из описания")
    else:
        add_missing_critical(
            report,
            "Товар / услуга",
            "Не указано, что именно вы приобрели — телефон, куртка, "
            "доставка, курс, ремонт и т.п.",
        )

    # Техсложный товар — важно для ст. 18 (оговорки) и ст. 25 (запрет)
    if _TECH_COMPLEX_PRE.search(problem):
        add_known(
            report, "Техсложный товар",
            "Да — учтены оговорки ст. 18 ЗоЗПП и Пост. 924"
        )

    # Суть проблемы
    problem_kind = _match_first(problem, _PROBLEM_PATTERNS)
    if problem_kind:
        add_known(report, "Суть проблемы", problem_kind)
    elif _has_purchase_marker(problem) and len(problem) >= 40:
        # Пользователь купил + описал что-то длинное.
        # Если с опечатками — regex может не поймать, но суть явно есть.
        add_known(report, "Суть проблемы", "Из описания")
    else:
        add_missing_critical(
            report,
            "Суть проблемы",
            "Не ясно, что именно не так: товар сломан, не подошёл, "
            "услуга оказана некачественно, продавец отказал в возврате и т.п.",
        )

    # Дата покупки — опционально
    if date_bought:
        add_known(report, "Дата покупки", date_bought)
    else:
        in_problem = _DATE_PATTERN.search(problem)
        if in_problem:
            add_known(report, "Дата покупки", in_problem.group(0))
        else:
            add_missing_optional(
                report,
                "Дата покупки",
                "Когда купили — важно для соблюдения сроков предъявления требований.",
            )

    # ─── Оговорка ст. 18: 15 дней для техсложных товаров ───
    if scenario == "defect" and _TECH_COMPLEX_PRE.search(problem):
        parsed_date = _parse_purchase_date(date_bought)
        if not parsed_date:
            in_problem_date = _DATE_PATTERN.search(problem)
            if in_problem_date:
                parsed_date = _parse_purchase_date(in_problem_date.group(0))

        if parsed_date:
            days = (_dt.date.today() - parsed_date).days
            if days > 15:
                add_known(
                    report,
                    "Срок с момента покупки",
                    f"{days} дней — больше 15",
                )
                add_missing_optional(
                    report,
                    "Существенность недостатка",
                    "По ст. 18 ЗоЗПП после 15 дней продавец вправе "
                    "предложить ремонт вместо возврата денег, ЕСЛИ "
                    "недостаток не существенный. Опишите подробнее: "
                    "полная неработоспособность, повторный ремонт, "
                    "невозможность ремонта и т.п.",
                )
            else:
                add_known(
                    report,
                    "Срок с момента покупки",
                    f"{days} дней — в пределах 15",
                )

    return report