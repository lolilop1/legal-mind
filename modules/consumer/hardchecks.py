"""Legal Mind — Module 1: consumer rights complaint hard checks.

Hard-check для претензии по защите прав потребителей.
Работает ДО LLM. Отсекает:
- слишком короткие / пустые описания
- явные ошибки модуля (про соседей или про УК — там свои модули)
- случаи без конкретики о товаре/услуге
- случаи без продавца

Emergency пока НЕ обрабатываем: потребительские споры не угрожают жизни.
"""

from __future__ import annotations

import re
from typing import Optional


_ALPHABET_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")


# ─── Явно про соседей / шум ───
_NEIGHBOR_NOISE_MARKERS = (
    "сосед шумит", "соседи шумят", "сосед сверху", "сосед снизу",
    "за стеной шум", "громкая музыка", "не дают спать",
    "нарушают тишину", "шум по ночам",
)


# ─── Явно про содержание дома (УК) ───
_UK_MARKERS = (
    "подъезд не убира", "в подъезде не убира", "не убирают подъезд",
    "управляющая компания", "ук не ", "батареи холодные",
    "холодные батареи", "течёт крыша", "течет крыша",
    "не работает лифт", "не чистят снег",
)


# ─── Маркеры потребительского спора ───
_CONSUMER_MARKERS = (
    # Покупка / заказ
    "купил", "купила", "заказал", "заказала", "приобрёл", "приобрела",
    "оплатил", "оплатила",
    # Товар / услуга
    "товар", "продавец", "магазин", "маркетплейс", "доставк",
    "услуг", "исполнител", "подрядчик",
    # Проблема
    "брак", "сломал", "не работает", "не работают", "дефект",
    "не подошл", "не подходит", "вернул", "вернула", "возврат",
    "не оказал", "не выполнил", "некачествен",
    # Маркетплейсы
    "ozon", "озон", "wildberries", "вайлдберриз", "avito", "авито",
)


def _normalize(text: object) -> str:
    s = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    return s


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(m in text for m in markers)


def _stop(reason: str) -> dict:
    """Возвращает стоп-сигнал в том же формате, что uk/noise."""
    return {
        "stop": True,
        "emergency": False,
        "stop_reason": reason,
        "описание_проблемы_формальное": None,
        "применимая_норма": None,
    }


def hard_pre_check(user_data: dict) -> Optional[dict]:
    """Проверки для жалобы потребителя. None — всё ок, идём к LLM."""
    problem = _normalize(user_data.get("проблема", ""))
    seller = (user_data.get("продавец") or "").strip()

    # 1. Too short.
    if len(problem) < 10:
        return _stop(
            "Описание проблемы слишком короткое — уточните, что именно случилось.",
        )

    # 2. Alphabet check.
    if not _ALPHABET_RE.search(problem):
        return _stop(
            "Описание не содержит текста — опишите проблему словами.",
        )

    # 3. Явная ошибка модуля: соседи / шум.
    if _has_any(problem, _NEIGHBOR_NOISE_MARKERS):
        return _stop(
            "Похоже, это про соседей и шум. Для этого случая нужен "
            "другой модуль — «Жалоба на нарушение тишины».",
        )

    # 4. Явная ошибка модуля: содержание дома (УК).
    if _has_any(problem, _UK_MARKERS):
        return _stop(
            "Похоже, это про содержание общего имущества дома. "
            "Для этого случая нужен модуль «Жалоба в управляющую компанию».",
        )

    # 5. Не похоже на потребительский спор — нет маркеров товара/услуги.
    if not _has_any(problem, _CONSUMER_MARKERS):
        return _stop(
            "Не похоже на потребительский спор. Опишите, что за товар "
            "или услугу вы приобрели и что с ними не так.",
        )

    # 6. Нет продавца.
    if not seller:
        return _stop(
            "Не указан продавец или исполнитель. Без этого претензию "
            "составить нельзя — укажите название магазина, компании "
            "или маркетплейса.",
        )

    # 7. Адрес продавца — обязателен для юрлиц / ИП / самозанятых.
    seller_address = (user_data.get("адрес_продавца") or "").strip()
    seller_link = (user_data.get("ссылка_продавца") or "").strip()

    if not seller_address and _is_legal_entity(seller):
        return _stop(
            "Не указан адрес продавца. Для организации или ИП его можно "
            "найти в ЕГРЮЛ/ЕГРИП, в чеке или на сайте. Без адреса претензию "
            "некуда отправить.",
        )

    # Физлицо: без адреса и без ссылки — претензия бессмысленна.
    if not seller_address and not seller_link:
        return _stop(
            "Для продавца-физлица нужен хотя бы один идентификатор: "
            "либо адрес, либо ссылка на профиль/объявление (Авито, "
            "Telegram, ВК). Без этого претензию некуда отправить, "
            "а в суде невозможно идентифицировать ответчика.",
        )

    return None


_KNOWN_MARKETPLACES = (
    "ozon", "озон",
    "wildberries", "вайлдберриз",
    "яндекс маркет", "яндекс.маркет", "yandex market",
    "avito", "авито",
    "мегамаркет", "megamarket",
    "aliexpress", "алиэкспресс",
    "kazan express", "казан экспресс",
    "lamoda", "ламода",
    "sbermegamarket", "сбермегамаркет",
    "детский мир", "detmir",
)


_LEGAL_PREFIXES = ("ООО", "АО", "ПАО", "ЗАО", "ОАО", "НКО",
                   "МУП", "ГУП", "ТСЖ", "ТД", "ТЦ")


def _is_legal_entity(seller: str) -> bool:
    """True если продавец похож на организацию, ИП или самозанятого."""
    s = (seller or "").strip().lower()
    if not s:
        return True  # пусто → требуем адрес (консервативно)

    upper = s.upper()
    for prefix in _LEGAL_PREFIXES:
        if upper.startswith(prefix + " ") or upper.startswith(prefix + "."):
            return True

    if upper.startswith("ИП ") or upper.startswith("ИП."):
        return True

    if "самозанят" in s:
        return True

    # Известные маркетплейсы — юрлица
    if any(m in s for m in _KNOWN_MARKETPLACES):
        return True

    # Физлицо без статуса
    return False