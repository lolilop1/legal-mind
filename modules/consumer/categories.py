"""Справочник категорий товаров/услуг для потребительских претензий.

Категория — параметр (не отдельный конфиг). Влияет на:
- PDF-подзаголовок: «о возврате стоимости смартфона» вместо «товара»
- LLM-hints: доп. правила для категории
- tech_complex: попадает ли под Пост. 924 (техсложные)

Поля:
  code         — код категории
  title        — название в родительном падеже (для PDF)
  keywords     — regex-паттерны для авто-детекта
  group        — группа (для UI в новом сайте)
  tech_complex — True если Пост. 924 (нельзя вернуть за 14 дней)
"""

from __future__ import annotations

import re


# ═══ Категории ═══
CATEGORIES: dict[str, dict] = {
    # ─── Электроника ───
    "smartphone": {
        "title": "смартфона",
        "keywords": r"смартфон|телефон|айфон|iphone|samsung|самсунг|сяоми|xiaomi|"
                    r"хуавей|huawei|оппо|oppo|виво|vivo|реалми|realme|"
                    r"пиксель|pixel|хонор|honor|мобильник",
        "group": "Электроника",
        "tech_complex": True,
    },
    "laptop": {
        "title": "ноутбука",
        "keywords": r"ноутбук|ноут|макбук|macbook|лэптоп|laptop|"
                    r"азус|asus|леново|lenovo|ацер|acer|хп\b|hp\b|"
                    r"де[л]|dell|мси\b|msi|тайвань|тайвань",
        "group": "Электроника",
        "tech_complex": True,
    },
    "desktop": {
        "title": "компьютера",
        "keywords": r"компьютер|системн\w*\s*блок|моноблок|пк\b|"
                    r"мат\.?плат|видеокарт|процессор|ssd|ж[её]стк\w*\s*диск",
        "group": "Электроника",
        "tech_complex": True,
    },
    "tablet": {
        "title": "планшета",
        "keywords": r"планшет|ipad|айпад|tab\b|galaxy tab",
        "group": "Электроника",
        "tech_complex": True,
    },
    "tv": {
        "title": "телевизора",
        "keywords": r"телевизор|\bтв\b|smart\s*tv|"
                    r"lg\b|sony|сони|филипс|philips|шарп|sharp",
        "group": "Электроника",
        "tech_complex": True,
    },
    "headphones": {
        "title": "наушников",
        "keywords": r"наушник|airpods|аирподс|\bгарнитур|"
                    r"jbl|bose|bose|с[оо]ни",
        "group": "Электроника",
        "tech_complex": False,
    },
    "camera": {
        "title": "фотоаппарата",
        "keywords": r"фотоаппарат|камер|nikon|canon|кэнон|"
                    r"объектив|зеркалк|беззеркалк",
        "group": "Электроника",
        "tech_complex": True,
    },
    "console": {
        "title": "игровой приставки",
        "keywords": r"playstation|плейстейшен|\bps[45]\b|xbox|"
                    r"nintendo|нинтендо|приставк",
        "group": "Электроника",
        "tech_complex": True,
    },
    "smartwatch": {
        "title": "умных часов",
        "keywords": r"умн\w*\s*час|smartwatch|apple watch|"
                    r"\bфитнес.{0,5}браслет|mi band",
        "group": "Электроника",
        "tech_complex": True,
    },
    "ereader": {
        "title": "электронной книги",
        "keywords": r"электронн\w*\s*книг|e-?reader|kindle|"
                    r"\bпокетбук|pocketbook",
        "group": "Электроника",
        "tech_complex": True,
    },
    "monitor": {
        "title": "монитора",
        "keywords": r"монитор|дисплей\s+для|"
                    r"\bdell\b.*monitor|\blg\b.*monitor",
        "group": "Электроника",
        "tech_complex": True,
    },
    "printer": {
        "title": "принтера",
        "keywords": r"принтер|\bмфу\b|сканер|"
                    r"hp\b.*printer|canon.*printer|epson",
        "group": "Электроника",
        "tech_complex": True,
    },

    # ─── Бытовая техника ───
    "fridge": {
        "title": "холодильника",
        "keywords": r"холодильник|морозильник|морозилк|"
                    r"\bхолод\.?\s*камер|indesit|атлант|"
                    r"\blg\b.*холод|samsung.*холод|bosch.*холод",
        "group": "Бытовая техника",
        "tech_complex": True,
    },
    "washer": {
        "title": "стиральной машины",
        "keywords": r"стиральн\w*\s*машин|стиралк|"
                    r"indesit|lg.*стир|samsung.*стир|bosch.*стир",
        "group": "Бытовая техника",
        "tech_complex": True,
    },
    "dishwasher": {
        "title": "посудомоечной машины",
        "keywords": r"посудомоечн|посудомойк|dishwasher",
        "group": "Бытовая техника",
        "tech_complex": True,
    },
    "vacuum": {
        "title": "пылесоса",
        "keywords": r"пылесос|robot\s*vacuum|робот.{0,10}пылесос|"
                    r"dyson|дайсон",
        "group": "Бытовая техника",
        "tech_complex": False,
    },
    "microwave": {
        "title": "микроволновой печи",
        "keywords": r"микроволнов|\bсвч\b",
        "group": "Бытовая техника",
        "tech_complex": True,
    },
    "multicooker": {
        "title": "мультиварки",
        "keywords": r"мультиварк|скороварк|"
                    r"\bредмонд|redmond|мулинекс|moulinex",
        "group": "Бытовая техника",
        "tech_complex": False,
    },
    "coffeemaker": {
        "title": "кофемашины",
        "keywords": r"кофемашин|кофеварк|"
                    r"delonghi|де[л]онги|jura|нуспо|nespresso",
        "group": "Бытовая техника",
        "tech_complex": True,
    },
    "ac": {
        "title": "кондиционера",
        "keywords": r"кондиционер|\bсплит.{0,5}систем|"
                    r"daikin|дайкин|mitsubishi|to[sh]iba",
        "group": "Бытовая техника",
        "tech_complex": True,
    },
    "iron": {
        "title": "утюга",
        "keywords": r"\bутюг|отпаривател|"
                    r"philips.*утюг|tefal|тефаль",
        "group": "Бытовая техника",
        "tech_complex": False,
    },
    "hairdryer": {
        "title": "фена",
        "keywords": r"\bфен\b|стайлер|выпрямител.{0,10}волос",
        "group": "Бытовая техника",
        "tech_complex": False,
    },
    "blender": {
        "title": "блендера",
        "keywords": r"блендер|миксер|кухонн\w*\s*комбайн",
        "group": "Бытовая техника",
        "tech_complex": False,
    },
    "kettle": {
        "title": "электрочайника",
        "keywords": r"электрочайник|чайник|термопот",
        "group": "Бытовая техника",
        "tech_complex": False,
    },
    "electric_stove": {
        "title": "электроплиты",
        "keywords": r"электроплит|электродуховк|варочн\w*\s*панел",
        "group": "Бытовая техника",
        "tech_complex": True,
    },
    "water_heater": {
        "title": "водонагревателя",
        "keywords": r"водонагревател|бойлер|"
                    r"\bарiston|ariston|electrolux.*водонагр",
        "group": "Бытовая техника",
        "tech_complex": True,
    },
    "gas_boiler": {
        "title": "газового котла",
        "keywords": r"газов\w*\s*котел|\bкотел\b|"
                    r"baxi|бакси|navien|навьен|viessmann",
        "group": "Бытовая техника",
        "tech_complex": True,
    },

    # ─── Одежда / обувь ───
    "jacket": {
        "title": "куртки",
        "keywords": r"\bкуртк|пуховик|\bпарк[аи]\b|"
                    r"\bветровк|\bбомбер|\bкосух",
        "group": "Одежда",
        "tech_complex": False,
    },
    "coat": {
        "title": "пальто",
        "keywords": r"\bпальто|\bшуба|\bполушубок|\bдубленк",
        "group": "Одежда",
        "tech_complex": False,
    },
    "dress": {
        "title": "платья",
        "keywords": r"\bплать|\bсарафан|\bюбк",
        "group": "Одежда",
        "tech_complex": False,
    },
    "jeans": {
        "title": "джинсов",
        "keywords": r"джинс|\bбрюк|\bштан|\bлегинс",
        "group": "Одежда",
        "tech_complex": False,
    },
    "shirt": {
        "title": "рубашки",
        "keywords": r"\bрубашк|\bблузк|\bфутболк|\bмайк|\bтоп\b",
        "group": "Одежда",
        "tech_complex": False,
    },
    "sweater": {
        "title": "свитера",
        "keywords": r"\bсвитер|\bсвитшот|\bхуди|\bтолстовк|\bкардиган|\bджемпер",
        "group": "Одежда",
        "tech_complex": False,
    },
    "shoes": {
        "title": "обуви",
        "keywords": r"\bобув|\bботинк|\bсапог|\bтуфл|"
                    r"\bсандал|\bбосоножк|\bмокасин|\bлофер",
        "group": "Обувь",
        "tech_complex": False,
    },
    "sneakers": {
        "title": "кроссовок",
        "keywords": r"\bкроссовк|nike|найк|adidas|адидас|"
                    r"new balance|puma|пума|asics|асикс",
        "group": "Обувь",
        "tech_complex": False,
    },
    "bag": {
        "title": "сумки",
        "keywords": r"\bсумк|\bрюкзак|\bчемодан|\bпортфел|\bклатч|\bкошел[её]к",
        "group": "Одежда",
        "tech_complex": False,
    },
    "belt": {
        "title": "ремня",
        "keywords": r"\bремень|\bремн|\bподтяжк|\bгалстук|\bбабочк",
        "group": "Одежда",
        "tech_complex": False,
    },

    # ─── Мебель ───
    "sofa": {
        "title": "дивана",
        "keywords": r"\bдиван|\bкушетк|\bтахт|\bуголок\b.*мягк",
        "group": "Мебель",
        "tech_complex": True,
    },
    "armchair": {
        "title": "кресла",
        "keywords": r"\bкресл",
        "group": "Мебель",
        "tech_complex": True,
    },
    "wardrobe": {
        "title": "шкафа",
        "keywords": r"\bшкаф|\bгардероб|\bстенк.*мебел",
        "group": "Мебель",
        "tech_complex": True,
    },
    "table": {
        "title": "стола",
        "keywords": r"\bстол\b|\bстолешниц|\bжурнальн.*стол|"
                    r"\bобеденн.*стол|\bписьменн.*стол",
        "group": "Мебель",
        "tech_complex": True,
    },
    "chair": {
        "title": "стула",
        "keywords": r"\bстул|\bтабурет|\bбарн.*стул",
        "group": "Мебель",
        "tech_complex": True,
    },
    "bed": {
        "title": "кровати",
        "keywords": r"\bкроват|\bдиван.{0,5}кроват",
        "group": "Мебель",
        "tech_complex": True,
    },
    "mattress": {
        "title": "матраса",
        "keywords": r"\bматрас|\bтоппер",
        "group": "Мебель",
        "tech_complex": True,
    },
    "chest": {
        "title": "комода",
        "keywords": r"\bкомод|\bтумб|\bполк",
        "group": "Мебель",
        "tech_complex": True,
    },

    # ─── Косметика / гигиена ───
    "perfume": {
        "title": "духов",
        "keywords": r"\bдух[ио]\b|парфюм|туалетн\w*\s*вод|"
                    r"\bодеколон|\bаромат\b",
        "group": "Косметика",
        "tech_complex": False,
    },
    "cosmetics": {
        "title": "косметики",
        "keywords": r"косметик|\bкрем\b|\bмаск[аиу]\b|"
                    r"\bпомад|\bтушь|\bпомаз|\bконсилер|\bхайлайтер",
        "group": "Косметика",
        "tech_complex": False,
    },
    "haircare": {
        "title": "средства для волос",
        "keywords": r"\bшампун|\bбальзам|\bкондиционер.{0,10}волос|"
                    r"\bмаск.{0,10}волос|\bлак.{0,5}волос",
        "group": "Косметика",
        "tech_complex": False,
    },

    # ─── Продукты ───
    "dairy": {
        "title": "молочных продуктов",
        "keywords": r"\bмолок|\bкефир|\bтворог|\bсыр\b|\bсметан|"
                    r"\bйогурт|\bмасл[оа]\b|\bряженк",
        "group": "Продукты",
        "tech_complex": False,
    },
    "meat": {
        "title": "мяса",
        "keywords": r"\bмяс|\bколбас|\bсосиск|\bкуриц|\bкури[нц]|"
                    r"\bрыб|\bфарш|\bбекон",
        "group": "Продукты",
        "tech_complex": False,
    },
    "bread": {
        "title": "хлеба",
        "keywords": r"\bхлеб|\bбулк|\bбатон|\bбублик|\bбагет",
        "group": "Продукты",
        "tech_complex": False,
    },
    "grocery": {
        "title": "продуктов",
        "keywords": r"\bпродукт|\bеда\b|\bконсерв|\bкрупа|\bмакарон|"
                    r"\bчай\b|\bкофе\b|\bсок\b|\bвод[аыу]\b.*питьев",
        "group": "Продукты",
        "tech_complex": False,
    },
    "baby_food": {
        "title": "детского питания",
        "keywords": r"детск\w*\s*питани|\bпюре\b.*дет|смес[ьи].{0,10}дет",
        "group": "Продукты",
        "tech_complex": False,
    },

    # ─── Лекарства / медизделия ───
    "medicine": {
        "title": "лекарства",
        "keywords": r"лекарств|\bпрепарат|\bтаблетк|\bмаз[ьи]\b|"
                    r"\bкапл|\bсироп|\bвитамин|\bбад\b|"
                    r"\bантибиотик|\bобезболив",
        "group": "Аптека",
        "tech_complex": False,
    },
    "medical_device": {
        "title": "медицинского изделия",
        "keywords": r"тонометр|глюкометр|\bтермометр|"
                    r"ингалятор|\bнебулайзер|пульсоксиметр|"
                    r"контактн\w*\s*линз",
        "group": "Аптека",
        "tech_complex": False,
    },

    # ─── Ювелирка ───
    "jewelry": {
        "title": "ювелирного изделия",
        "keywords": r"ювелир|золот|серебр|\bкольц|\bсерьг|"
                    r"\bцепочк|\bбраслет|\bкулон|бриллиант|"
                    r"обручальн",
        "group": "Ювелирка",
        "tech_complex": False,
    },

    # ─── Детские товары ───
    "stroller": {
        "title": "детской коляски",
        "keywords": r"коляск|\bлюльк|прогулочн.{0,10}блок",
        "group": "Детские товары",
        "tech_complex": False,
    },
    "car_seat": {
        "title": "автокресла",
        "keywords": r"автокресл|\bбустер|детск\w*\s*кресл",
        "group": "Детские товары",
        "tech_complex": False,
    },
    "toys": {
        "title": "игрушки",
        "keywords": r"\bигрушк|\bконструктор|\bкукл|\bмашинк.{0,5}дет|"
                    r"\bпогремушк|\bмягк.{0,5}игрушк",
        "group": "Детские товары",
        "tech_complex": False,
    },
    "kids_clothes": {
        "title": "детской одежды",
        "keywords": r"детск\w*\s*(?:одежд|куртк|комбинезон|бодик)|"
                    r"\bползунк|\bраспашонк|\bпеленк",
        "group": "Детские товары",
        "tech_complex": False,
    },

    # ─── Спорт ───
    "bike": {
        "title": "велосипеда",
        "keywords": r"велосипед|\bбайк\b|\bвелик\b|"
                    r"\bсамокат|\bскейтборд",
        "group": "Спорт",
        "tech_complex": True,
    },
    "fitness": {
        "title": "тренажёра",
        "keywords": r"тренажер|\bгантел|\bштанг|\bбегов.{0,5}дорожк|"
                    r"\bэллиптическ|\bорбитрек",
        "group": "Спорт",
        "tech_complex": True,
    },
    "sport_clothes": {
        "title": "спортивной одежды",
        "keywords": r"спортивн\w*\s*(?:одежд|костюм)|"
                    r"\bтермобель|\bспортивн.{0,10}штаны",
        "group": "Спорт",
        "tech_complex": False,
    },

    # ─── Стройматериалы ───
    "tile": {
        "title": "плитки",
        "keywords": r"\bплитк|керамогранит|\bкафел",
        "group": "Стройматериалы",
        "tech_complex": False,
    },
    "laminate": {
        "title": "ламината",
        "keywords": r"\bламинат|\bпаркет|\bлинолеум|\bвинил.{0,5}покрыт",
        "group": "Стройматериалы",
        "tech_complex": False,
    },
    "wallpaper": {
        "title": "обоев",
        "keywords": r"\bобои|\bобой|\bфлизелинов",
        "group": "Стройматериалы",
        "tech_complex": False,
    },
    "paint": {
        "title": "краски",
        "keywords": r"\bкраск|\bэмал[ьи]|\bгрунтовк|\bштукатурк|"
                    r"\bшпаклевк|\bшпатлевк",
        "group": "Стройматериалы",
        "tech_complex": False,
    },
    "tools": {
        "title": "инструмента",
        "keywords": r"\bдрел|\bперфоратор|\bшуруповерт|"
                    r"\bболгарк|\bлобзик|\bстанок|\bкомпрессор|"
                    r"\bэлектроинструмент|\bпила\b",
        "group": "Стройматериалы",
        "tech_complex": True,
    },

    # ─── Авто / мото ───
    "tires": {
        "title": "шин",
        "keywords": r"\bшин[ыау]|\bпокрышк|\bавтошин",
        "group": "Авто",
        "tech_complex": False,
    },
    "auto_parts": {
        "title": "автозапчасти",
        "keywords": r"автозапчаст|\bзапчаст|\bбампер|\bфар[ыа]\b|"
                    r"\bстартер|\bгенератор.{0,5}авто|"
                    r"\bтормозн.{0,5}колодк",
        "group": "Авто",
        "tech_complex": False,
    },
    "auto_oil": {
        "title": "автомасла",
        "keywords": r"автомасл|моторн\w*\s*масл|"
                    r"\bантифриз|\bтосол",
        "group": "Авто",
        "tech_complex": False,
    },
    "battery": {
        "title": "аккумулятора",
        "keywords": r"аккумулятор|\bа[кк]б\b",
        "group": "Авто",
        "tech_complex": True,
    },
    "moto": {
        "title": "мотоцикла",
        "keywords": r"мотоцикл|\bмопед|\bскутер|\bмотороллер",
        "group": "Авто",
        "tech_complex": True,
    },

    # ─── Услуги ───
    "repair_flat": {
        "title": "ремонта квартиры",
        "keywords": r"ремонт.{0,10}квартир|ремонт.{0,10}дом|"
                    r"отделк.{0,10}квартир|ремонтн\w*\s*работ",
        "group": "Услуги",
        "tech_complex": False,
    },
    "repair_auto": {
        "title": "ремонта автомобиля",
        "keywords": r"ремонт.{0,10}(?:авто|машин)|автосервис|"
                    r"\bсто\b.{0,10}ремонт",
        "group": "Услуги",
        "tech_complex": False,
    },
    "education": {
        "title": "образовательных услуг",
        "keywords": r"\bкурс|обучени|тренинг|вебинар|"
                    r"образовательн|\bшкол|репетитор|"
                    r"\bинститут|\bколледж|\bуниверситет",
        "group": "Услуги",
        "tech_complex": False,
    },
    "medical_service": {
        "title": "медицинских услуг",
        "keywords": r"стоматолог|косметолог|медицинск|"
                    r"\bклиник|\bврач|\bимплант|\bбрекет|"
                    r"\bплатн\w*\s*медицин",
        "group": "Услуги",
        "tech_complex": False,
    },
    "tourism": {
        "title": "туристических услуг",
        "keywords": r"\bтур[ыа]?\b|пут[её]вк|туроператор|турагент|"
                    r"\bотел|\bгостиниц|\bкурорт|авиабилет",
        "group": "Услуги",
        "tech_complex": False,
    },
    "bank": {
        "title": "банковских услуг",
        "keywords": r"\bбанк|\bкредит|микрозайм|\bмфо\b|"
                    r"кредитн\w*\s*карт|дебетов\w*\s*карт",
        "group": "Услуги",
        "tech_complex": False,
    },
    "insurance": {
        "title": "страховых услуг",
        "keywords": r"страхов|\bосаго|\bкаско|\bдмс\b|"
                    r"страхов\w*\s+(?:выплат|возмещен|преми)",
        "group": "Услуги",
        "tech_complex": False,
    },
    "legal": {
        "title": "юридических услуг",
        "keywords": r"юридическ|\bюрист|\bадвокат|\bнотариус",
        "group": "Услуги",
        "tech_complex": False,
    },
    "delivery": {
        "title": "доставки",
        "keywords": r"\bдоставк|\bкурьер|\bпосылк|"
                    r"\bпункт.{0,5}выдач|\bпвз\b",
        "group": "Услуги",
        "tech_complex": False,
    },
    "beauty": {
        "title": "бытовых услуг",
        "keywords": r"\bстрижк|\bманикюр|\bпедикюр|\bкосметолог|"
                    r"\bмассаж|\bнаращиван|\bокрашиван|\bпарикмахер",
        "group": "Услуги",
        "tech_complex": False,
    },
    "digital": {
        "title": "цифровых услуг",
        "keywords": r"подписк|\bприложени|\bигр[аыу]\b|"
                    r"\bсофт|\bпрограмм|\bкурс.{0,5}онлайн",
        "group": "Услуги",
        "tech_complex": False,
    },
}


_COMPILED: list[tuple[str, re.Pattern]] = [
    (code, re.compile(data["keywords"], re.IGNORECASE))
    for code, data in CATEGORIES.items()
]


def detect_category(text: str) -> str | None:
    """Определяет категорию товара/услуги по тексту.

    Returns: code категории или None.
    """
    if not text:
        return None
    s = text.lower()
    for code, pat in _COMPILED:
        if pat.search(s):
            return code
    return None


def get_category(code: str) -> dict | None:
    """Возвращает данные категории по коду."""
    if not code:
        return None
    data = CATEGORIES.get(code)
    if not data:
        return None
    return {"code": code, **data}


def all_codes() -> list[str]:
    return sorted(CATEGORIES.keys())
