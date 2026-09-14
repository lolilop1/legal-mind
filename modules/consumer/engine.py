"""Legal Mind — Module 1: consumer rights complaint engine.

Один движок для всех 4 сценариев (defect, return14, marketplace, service).
Читает CONFIG, строит промпт, гонит через LLM, валидирует ответ.

Возвращает dict в том же формате, что process_uk/process_noise в app.py:
    {"kind": "ok" | "stop" | "error", "parsed": {...}, "retried": bool}
"""

from __future__ import annotations

import json
import re

from core.llm import call_alice_flash
from modules.consumer.categories import get_category, detect_category
from modules.consumer.entity_check import check_consumer_numeric_recall
from modules.consumer.demands import get_demand


# ─── Какой конфиг использовать для какого сценария ───
def _get_config(scenario: str):
    """Импортирует конфиг по коду сценария. None если сценарий неизвестен."""
    if scenario == "defect":
        from modules.consumer.configs.defect import CONFIG
        return CONFIG
    if scenario == "return14":
        from modules.consumer.configs.return14 import CONFIG
        return CONFIG
    if scenario == "marketplace":
        from modules.consumer.configs.marketplace import CONFIG
        return CONFIG
    if scenario == "service":
        from modules.consumer.configs.service import CONFIG
        return CONFIG
    return None


# ─── Шаблон системного промпта ───
_PROMPT_TEMPLATE = """Ты — модуль нормализации данных для юридического сервиса.
Твоя задача: превратить неформальное описание потребительского спора
в строгую формулировку для досудебной претензии.

СЦЕНАРИЙ: {title} ({article})

СТРОГИЕ ПРАВИЛА:
1. Не придумывай факты, которых пользователь не сообщал.
2. Не придумывай нормы, которых нет в списке ниже.
3. Не давай оценок, не обвиняй конкретных лиц, только фиксируй факты.
4. Тон — сухой, официальный, без эмоциональной окраски.
5. Сохрани ВСЕ существенные обстоятельства: название товара/услуги,
   продавца, дату покупки, цену, суть недостатка, требование потребителя.

{hints}

РАЗРЕШЁННЫЕ ССЫЛКИ НА НОРМЫ (только эти):
{norms}

ФОРМАТ ВЫХОДА (строго JSON):
{{
  "описание_проблемы_формальное": "...",
  "требование": "...",
  "применимые_нормы": [
    ...
  ]
}}"""


_CORRECTIVE_NUMERIC = """Твой предыдущий ответ добавил данные, которых не было во входе.

Исходные данные (JSON):
{input_json}

Твой предыдущий ответ:
{previous}

Эти значения НЕ встречаются во входных данных и должны быть УДАЛЕНЫ или ЗАМЕНЕНЫ на нейтральные формулировки:
{missing}

Перепиши ответ БЕЗ этих значений. Если дата или цена не указана пользователем — не упоминай её вообще. Верни СТРОГО тот же JSON-формат."""


def _build_prompt(config: dict, cat_data: dict | None = None,
                  chosen_demand: dict | None = None) -> str:
    hints_list = list(config["llm_hints"])
    if chosen_demand:
        # Требование выбрано юзером — LLM ОБЯЗАНА использовать его дословно
        hints_list.insert(0,
            "ПОЛЬЗОВАТЕЛЬ УЖЕ ВЫБРАЛ ТРЕБОВАНИЕ: «" +
            chosen_demand["wording"] + "». "
            "В поле \"требование\" верни ИМЕННО эту формулировку дословно. "
            "НЕ добавляй альтернативы («либо», «или»), не предлагай "
            "другие требования."
        )
    if cat_data:
        hints_list.insert(0,
            "КОНКРЕТНАЯ КАТЕГОРИЯ: " + cat_data["title"] + ". "
            "Сохрани название категории в описании (не обобщай)."
        )
        if cat_data.get("tech_complex"):
            hints_list.append(
                "ВАЖНО: товар технически сложный (Пост. 924). "
                "Учти оговорки ст. 18 ЗоЗПП про 15 дней."
            )
    hints = "\n".join(f"- {h}" for h in hints_list)
    norms = "\n".join(f'- "{n}"' for n in config["allowed_norms"])
    return _PROMPT_TEMPLATE.format(
        title=config["title"],
        article=config["article"],
        hints=hints,
        norms=norms,
    )

def _parse_llm_json(raw: str) -> dict:
    cleaned = (raw.strip()
               .removeprefix("```json").removeprefix("```")
               .removesuffix("```").strip())
    return json.loads(cleaned)


def _call_llm(instructions: str, user_input: str) -> dict:
    result = call_alice_flash(instructions, user_input, temperature=0.2, max_tokens=1200)
    if "error" in result:
        return {"error": result["error"]}
    raw = result.get("text", "")
    try:
        parsed = _parse_llm_json(raw)
    except json.JSONDecodeError as e:
        return {"error": f"Не удалось распарсить JSON: {e}", "raw_response": raw}
    return {"parsed": parsed, "raw_response": raw}


def process_consumer(user_data: dict, scenario: str,
                     category: str | None = None) -> dict:
    """Главная точка входа модуля 1.

    Args:
        user_data: поля формы (проблема, продавец, дата_покупки, требование…)
        scenario: "defect" | "return14" | "marketplace" | "service"
        category: код категории товара/услуги (опционально).
                  Если None — определится автоматически по тексту.

    Returns:
        {"kind": "ok"|"stop"|"error", "parsed": {...}, "retried": bool,
         "category": str|None, ...}
    """
    config = _get_config(scenario)
    if config is None:
        return {
            "kind": "error",
            "message": f"Неизвестный сценарий: {scenario!r}",
            "retried": False,
        }

    # Категория: если не задана — определяем по тексту
    if category is None:
        category = detect_category(user_data.get("проблема", ""))
    cat_data = get_category(category) if category else None

    # Требование, выбранное юзером (если есть) — приоритет над LLM
    chosen_demand = get_demand(user_data.get("требование_код", ""))

    prompt = _build_prompt(config, cat_data, chosen_demand)
    user_msg = json.dumps(user_data, ensure_ascii=False)

    a1 = _call_llm(prompt, user_msg)
    if "error" in a1:
        return {"kind": "error", "message": a1["error"], "retried": False}

    parsed = a1["parsed"]

    # ─── Валидация: обязательные поля ───
    required = {"описание_проблемы_формальное", "требование", "применимые_нормы"}
    if required - set(parsed):
        return {
            "kind": "error",
            "message": "Модель вернула неполный JSON",
            "retried": False,
        }

    # ─── Валидация: нормы только из whitelist ───
    allowed = set(config["allowed_norms"])
    got = set(parsed["применимые_нормы"])
    if not got.issubset(allowed):
        bad = got - allowed
        return {
            "kind": "error",
            "message": f"Модель использовала недопустимые нормы: {bad}",
            "retried": False,
        }

    # ─── Валидация: хотя бы одна якорная норма ───
    anchor_norms = config.get("anchor_norms", [])
    if anchor_norms:
        anchors_set = set(anchor_norms)
        if not (got & anchors_set):
            # LLM не вернула ни одной якорной нормы — добавляем первую вручную
            fallback = anchor_norms[0]
            parsed["применимые_нормы"] = [fallback] + list(parsed["применимые_нормы"])
            parsed["_anchor_fallback"] = True

    # ─── Валидация: непустое описание ───
    if not parsed["описание_проблемы_формальное"].strip():
        return {
            "kind": "error",
            "message": "Модель вернула пустое описание",
            "retried": False,
        }

    # ─── Жёсткая подмена требования, если юзер его выбрал ───
    if chosen_demand:
        parsed["требование"] = chosen_demand["wording"]

    # ─── Anti-hallucination: числа и даты только из user_data ───
    numeric_retried = False
    recall = check_consumer_numeric_recall(
        user_data, parsed["описание_проблемы_формальное"]
    )
    if not recall["ok"]:
        numeric_retried = True
        missing_str = "\n".join(
            f"- {m['kind']}: {m['value']}" for m in recall["missing"]
        )
        corrective = _CORRECTIVE_NUMERIC.format(
            input_json=json.dumps(user_data, ensure_ascii=False, indent=2),
            previous=parsed["описание_проблемы_формальное"],
            missing=missing_str,
        )
        a2 = _call_llm(prompt, corrective)
        if "error" not in a2 and "parsed" in a2:
            parsed2 = a2["parsed"]
            # Проверяем, что структура сохранилась
            if ({"описание_проблемы_формальное", "требование",
                 "применимые_нормы"} <= set(parsed2)):
                parsed = parsed2
                recall = check_consumer_numeric_recall(
                    user_data, parsed["описание_проблемы_формальное"]
                )

    # Если и после ретрая остались выдуманные числа — вырезаем их
    # из текста (безопаснее, чем оставить галлюцинацию в PDF).
    if not recall["ok"]:
        txt = parsed["описание_проблемы_формальное"]
        for m in recall["missing"]:
            if m["kind"] == "date":
                # Убираем саму дату и соседние предлоги
                txt = re.sub(
                    r"\s*(?:от|с|в|на)\s*" + re.escape(m["value"]),
                    "", txt, flags=re.IGNORECASE,
                )
                txt = txt.replace(m["value"], "")
            elif m["kind"] == "price":
                # Убираем «стоимостью X рублей», «за X руб», «ценой X».
                # Порядок альтернатив важен: «рублей» ПЕРЕД «руб\.?»,
                # иначе «руб» съест «рублей» и оставит огрызок «лей».
                pat = re.compile(
                    r"(?:стоимость[юия]|стоимость|цена|ценой|цену|цены|за)\s+"
                    r"\b" + re.escape(m["value"]) + r"\s*"
                    r"(?:рублей|руб\.?|₽)?",
                    re.IGNORECASE,
                )
                txt = pat.sub("", txt)
        txt = re.sub(r"\s{2,}", " ", txt)
        txt = re.sub(r"\s+([.,;:])", r"\1", txt).strip()
        parsed["описание_проблемы_формальное"] = txt
        parsed["_numeric_stripped"] = True

    return {
        "kind": "ok",
        "parsed": parsed,
        "retried": numeric_retried,
        "stop_kind": None,
        "scenario": scenario,
        "category": category,
    }
