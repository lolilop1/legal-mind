"""Legal Mind — Module 1: consumer rights complaint engine.

Один движок для всех 4 сценариев (defect, return14, marketplace, service).
Читает CONFIG, строит промпт, гонит через LLM, валидирует ответ.

Возвращает dict в том же формате, что process_uk/process_noise в app.py:
    {"kind": "ok" | "stop" | "error", "parsed": {...}, "retried": bool}
"""

from __future__ import annotations

import json

from core.llm import call_alice_flash


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


def _build_prompt(config: dict) -> str:
    hints = "\n".join(f"- {h}" for h in config["llm_hints"])
    norms = "\n".join(f"- \"{n}\"" for n in config["allowed_norms"])
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


def process_consumer(user_data: dict, scenario: str) -> dict:
    """Главная точка входа модуля 1.

    Args:
        user_data: поля формы (проблема, продавец, дата_покупки, требование…)
        scenario: "defect" | "return14" | "marketplace" | "service"

    Returns:
        {"kind": "ok"|"stop"|"error", "parsed": {...}, "retried": bool, ...}
    """
    config = _get_config(scenario)
    if config is None:
        return {
            "kind": "error",
            "message": f"Неизвестный сценарий: {scenario!r}",
            "retried": False,
        }

    prompt = _build_prompt(config)
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

    return {
        "kind": "ok",
        "parsed": parsed,
        "retried": False,
        "stop_kind": None,
        "scenario": scenario,
    }