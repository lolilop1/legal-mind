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


# ─── Подтипы гарантийного случая (defect) ───
_DEFECT_SUBTYPES: tuple[tuple[str, str, str], ...] = (
    (r"отказа\w*\s+(?:в\s+)?ремонт|"
     r"отказа\w*\s+прин(?:ять|имать)|"
     r"отказ\w*\s+прин(?:ять|имать)|"
     r"не\s+гарантийн|не\s+принима\w*\s+.*ремонт|"
     r"не\s+берут\s+в\s+ремонт|"
     r"сами\s+слома|не\s+наша\s+вина|"
     r"в\s+гарантии\s+отказ|отказ\w*\s+в\s+гарант|"
     r"сервис\w*\s+отказ",
     "Отказ в гарантийном ремонте",
     "ст. 18, 20 — продавец не вправе отказать без экспертизы"),
    (r"ремонт.{0,40}(?:больше|свыше|более|дольше|длится|идёт|идет|"
     r"тянется).{0,15}(?:45|месяц|год)|"
     r"ремонт.{0,40}третий\s+месяц|"
     r"45\s+дн\w*.{0,40}ремонт|"
     r"долго\s+ремонт|затянул\w*\s+ремонт|"
     r"ремонт\s+уже.{0,30}(?:месяц|год)|"
     r"ремонтируют\s+уже",
     "Просрочка ремонта (>45 дней)",
     "ст. 20 п. 1, 23 — неустойка 1% за каждый день свыше 45"),
    (r"брак|дефект|сломал|переста\w*\s+работать|"
     r"не\s+работает|неисправн|поврежден|"
     r"не\s+включает|вышел\s+из\s+строя",
     "Товар с недостатком",
     "ст. 18 — возврат/замена/ремонт"),
)


def _detect_defect_subtype(problem: str) -> tuple[str, str] | None:
    for pattern, label, hint in _DEFECT_SUBTYPES:
        if re.search(pattern, problem, re.IGNORECASE):
            return label, hint
    return None


# ─── Подтипы маркетплейса ───
_MARKETPLACE_SUBTYPES: tuple[tuple[str, str, str], ...] = (
    (r"не\s+доставил|не\s+пришл|не\s+привез|не\s+получил\s+товар|"
     r"просрочк|задержк|опаздыва|не\s+привезли|не\s+дошл|"
     r"\bне\s+пришёл|\bне\s+пришло|не\s+пришла\s+посылк|"
     r"месяц.*не\s+доставил|долго\s+жд|не\s+могу\s+дождаться",
     "Просрочка доставки",
     "ст. 23.1 — неустойка 0,5% за каждый день просрочки"),
    (r"брак|дефект|сломал|не\s+работа|трещин|повреж|"
     r"не\s+соответству|не\s+то\s+что\s+заказ",
     "Товар с недостатком",
     "ст. 26.1 + 18 — возврат/замена/ремонт"),
    (r"ввёл.*заблужд|обман|не\s+та\s+информац|"
     r"не\s+соответствует\s+описанию",
     "Недостоверная информация",
     "ст. 12 — возмещение убытков"),
)


def _detect_marketplace_subtype(problem: str) -> tuple[str, str] | None:
    for pattern, label, hint in _MARKETPLACE_SUBTYPES:
        if re.search(pattern, problem, re.IGNORECASE):
            return label, hint
    return None


# ─── Подтипы услуги (ст. 27-33 ЗоЗПП) ───
_SERVICE_SUBTYPES: tuple[tuple[str, str, str], ...] = (
    (r"просроч|позже|задерж|не в срок|срок.*наруш|обещал.*сдела|"
     r"должен был|опаздыва|затягив|не уложились?",
     "Нарушен срок выполнения",
     "ст. 27, 28 — неустойка 3% за каждый день просрочки"),
    (r"смет|дороже|доплати|превысил|не согласов|больше чем|"
     r"сказали.*стоить|оплатил.*дороже",
     "Смета превышена без согласования",
     "ст. 33 — исполнитель не вправе требовать доплату без согласования"),
    (r"отказ|передумал|не нужн|хочу отказ|больше не надо|"
     r"расторгнуть|вернуть.*деньги.*услуг",
     "Отказ от услуги",
     "ст. 32 — возврат минус фактические расходы исполнителя"),
    (r"некачествен|плохо|халтур|дефект|отклеива|"
     r"не выполн|испортил|брак",
     "Работа выполнена некачественно",
     "ст. 29, 30 — безвозмездное устранение или возврат"),
)


def _detect_service_subtype(problem: str) -> tuple[str, str] | None:
    for pattern, label, hint in _SERVICE_SUBTYPES:
        if re.search(pattern, problem, re.IGNORECASE):
            return label, hint
    return None


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

    # ─── Подтип гарантийного случая (defect) ───
    if scenario == "defect":
        subtype = _detect_defect_subtype(problem)
        if subtype:
            label, hint = subtype
            add_known(report, "Подтип гарантийного случая", f"{label} ({hint})")

    # ─── Подтип marketplace ───
    if scenario == "marketplace":
        subtype = _detect_marketplace_subtype(problem)
        if subtype:
            label, hint = subtype
            add_known(report, "Подтип маркетплейса", f"{label} ({hint})")

    # ─── Подтип услуги (только для service) ───
    if scenario == "service":
        subtype = _detect_service_subtype(problem)
        if subtype:
            label, hint = subtype
            add_known(report, "Подтип услуги", f"{label} ({hint})")

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