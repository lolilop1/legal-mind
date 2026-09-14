"""Модуль 2 — общий движок для документов по УК.

Читает CONFIG по doc_type, строит промпт, гоняет через LLM,
валидирует ответ. Спец-логика entity_check (в UK — важен recall
существенных фактов).

Возвращает dict в формате process_uk в app.py.
"""

from __future__ import annotations

import json

from core.llm import call_alice_flash
from modules.uk.entity_check import check_entity_recall


def _get_config(doc_type: str):
    """Импорт конфига по коду документа."""
    if doc_type == "uk":
        from modules.uk.configs.uk import CONFIG
        return CONFIG
    if doc_type == "gzhi":
        from modules.uk.configs.gzhi import CONFIG
        return CONFIG
    if doc_type == "rpn":
        from modules.uk.configs.rpn import CONFIG
        return CONFIG
    if doc_type == "prokuratura":
        from modules.uk.configs.prokuratura import CONFIG
        return CONFIG
    if doc_type == "damage":
        from modules.uk.configs.damage import CONFIG
        return CONFIG
    if doc_type == "pereraschet":
        from modules.uk.configs.pereraschet import CONFIG
        return CONFIG
    if doc_type == "zapros_info":
        from modules.uk.configs.zapros_info import CONFIG
        return CONFIG
    if doc_type == "pereraschet":
        from modules.uk.configs.pereraschet import CONFIG
        return CONFIG
    if doc_type == "kvitancia":
        from modules.uk.configs.kvitancia import CONFIG
        return CONFIG
    if doc_type == "ads":
        from modules.uk.configs.ads import CONFIG
        return CONFIG
    if doc_type == "tszh":
        from modules.uk.configs.tszh import CONFIG
        return CONFIG
    if doc_type == "kapremont":
        from modules.uk.configs.kapremont import CONFIG
        return CONFIG
    if doc_type == "municipality":
        from modules.uk.configs.municipality import CONFIG
        return CONFIG
    if doc_type == "act":
        from modules.uk.configs.act import CONFIG
        return CONFIG
    if doc_type == "s_o_s":
        from modules.uk.configs.s_o_s import CONFIG
        return CONFIG
    if doc_type == "rastorzhenie":
        from modules.uk.configs.rastorzhenie import CONFIG
        return CONFIG
    if doc_type == "snizhenie":
        from modules.uk.configs.snizhenie import CONFIG
        return CONFIG
    if doc_type == "roszhilnadzor":
        from modules.uk.configs.roszhilnadzor import CONFIG
        return CONFIG
    if doc_type == "fas":
        from modules.uk.configs.fas import CONFIG
        return CONFIG
    if doc_type == "mchs":
        from modules.uk.configs.mchs import CONFIG
        return CONFIG
    if doc_type == "ses":
        from modules.uk.configs.ses import CONFIG
        return CONFIG
    if doc_type == "zatoplenie":
        from modules.uk.configs.zatoplenie import CONFIG
        return CONFIG
    if doc_type == "pereplanirovka":
        from modules.uk.configs.pereplanirovka import CONFIG
        return CONFIG
    if doc_type == "parkovka":
        from modules.uk.configs.parkovka import CONFIG
        return CONFIG
    if doc_type == "reklama":
        from modules.uk.configs.reklama import CONFIG
        return CONFIG
    if doc_type == "tehdoc":
        from modules.uk.configs.tehdoc import CONFIG
        return CONFIG
    if doc_type == "neprozhivanie":
        from modules.uk.configs.neprozhivanie import CONFIG
        return CONFIG
    if doc_type == "otpusk":
        from modules.uk.configs.otpusk import CONFIG
        return CONFIG
    if doc_type == "isk_zozpp":
        from modules.uk.configs.isk_zozpp import CONFIG
        return CONFIG
    if doc_type == "isk_pereraschet":
        from modules.uk.configs.isk_pereraschet import CONFIG
        return CONFIG
    if doc_type == "isk_objazanie":
        from modules.uk.configs.isk_objazanie import CONFIG
        return CONFIG
    if doc_type == "os_obzhalovanie":
        from modules.uk.configs.os_obzhalovanie import CONFIG
        return CONFIG
    if doc_type == "predsedatel":
        from modules.uk.configs.predsedatel import CONFIG
        return CONFIG
    if doc_type == "avariynaya_komissiya":
        from modules.uk.configs.avariynaya_komissiya import CONFIG
        return CONFIG
    if doc_type == "kapremont_vznosy":
        from modules.uk.configs.kapremont_vznosy import CONFIG
        return CONFIG
    return None


_PROMPT_TEMPLATE = """Ты — модуль нормализации данных для юридического сервиса.
Твоя задача: превратить неформальное описание проблемы от пользователя
в строгую формулировку для документа: {title}.

СТРОГИЕ ПРАВИЛА:
1. Не придумывай факты, которых пользователь не сообщал.
2. Не придумывай нормы, которых нет в списке ниже.
3. Не давай оценок, не обвиняй конкретных лиц.
4. Тон — сухой, официальный, без эмоций.
5. Сохрани ВСЕ существенные обстоятельства.

{hints}

РАЗРЕШЁННЫЕ ССЫЛКИ НА НОРМЫ (только эти):
{norms}

ФОРМАТ ВЫХОДА (строго JSON):
{{
  "описание_проблемы_формальное": "...",
  "упоминание_повторного_обращения": "" или "...",
  "применимые_нормы": [...]
}}"""


def _build_prompt(config: dict) -> str:
    hints = "\n".join(f"- {h}" for h in config["llm_hints"])
    norms = "\n".join(f'- "{n}"' for n in config["allowed_norms"])
    return _PROMPT_TEMPLATE.format(
        title=config["title"], hints=hints, norms=norms,
    )


def _parse_llm_json(raw: str) -> dict:
    cleaned = (raw.strip()
               .removeprefix("```json").removeprefix("```")
               .removesuffix("```").strip())
    return json.loads(cleaned)


def _call_llm(instructions: str, user_input: str) -> dict:
    result = call_alice_flash(instructions, user_input,
                              temperature=0.2, max_tokens=1200)
    if "error" in result:
        return {"error": result["error"]}
    raw = result.get("text", "")
    try:
        parsed = _parse_llm_json(raw)
    except json.JSONDecodeError as e:
        return {"error": f"Не удалось распарсить JSON: {e}", "raw_response": raw}
    return {"parsed": parsed, "raw_response": raw}


CORRECTIVE_TEMPLATE = """Твой предыдущий ответ потерял существенные факты.

Исходное описание:
{problem}

Твой предыдущий ответ:
{previous}

Пропущены: {missing}.

Перепиши ответ заново, сохранив ВСЕ факты. Верни СТРОГО JSON."""


def process_uk(user_data: dict, doc_type: str = "uk") -> dict:
    """Главная точка входа модуля 2.

    Args:
        user_data: поля формы (проблема, адрес, дата_начала, ...)
        doc_type: uk | gzhi | rpn | prokuratura | damage

    Returns:
        {"kind": "ok"|"error", "parsed": {...}, "retried": bool, "doc_type": str}
    """
    config = _get_config(doc_type)
    if config is None:
        return {
            "kind": "error",
            "message": f"Неизвестный тип документа: {doc_type!r}",
            "retried": False,
        }

    instructions = _build_prompt(config)
    payload = {k: v for k, v in user_data.items() if k != "название"}
    user_msg = json.dumps(payload, ensure_ascii=False)

    a1 = _call_llm(instructions, user_msg)
    if "error" in a1:
        return {"kind": "error", "message": a1["error"], "retried": False}

    parsed = a1["parsed"]

    required = {"описание_проблемы_формальное", "применимые_нормы"}
    if required - set(parsed):
        return {"kind": "error", "message": "Модель вернула неполный JSON", "retried": False}

    allowed = set(config["allowed_norms"])
    got = set(parsed["применимые_нормы"])
    if not got.issubset(allowed):
        bad = got - allowed
        return {
            "kind": "error",
            "message": f"Модель использовала недопустимые нормы: {bad}",
            "retried": False,
        }

    if not parsed["описание_проблемы_формальное"].strip():
        return {"kind": "error", "message": "Модель вернула пустое описание", "retried": False}

    # Entity check — только для УК (важно сохранить существенные факты)
    retried = False
    if doc_type == "uk":
        recall = check_entity_recall(
            user_data.get("проблема", ""),
            user_data.get("дата_начала", ""),
            parsed["описание_проблемы_формальное"],
        )
        if not recall["ok"]:
            retried = True
            missing = ", ".join(f"{m['kind']}:{m['value']}" for m in recall["missing"])
            corrective = CORRECTIVE_TEMPLATE.format(
                problem=user_data.get("проблема", ""),
                previous=parsed["описание_проблемы_формальное"],
                missing=missing,
            )
            a2 = _call_llm(instructions, corrective)
            if "error" not in a2:
                parsed = a2["parsed"]

    return {
        "kind": "ok",
        "parsed": parsed,
        "retried": retried,
        "doc_type": doc_type,
    }
