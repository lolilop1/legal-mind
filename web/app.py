"""Legal Mind — Web application.

v3.1: session-based "my cases" list.
"""

import io
import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# ─── Добавляем корень проекта в sys.path ───
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ─── Загружаем .env ───
from dotenv import load_dotenv
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH if _ENV_PATH.exists() else None)

# ─── Импорты наших модулей ───
from flask import Flask, render_template, request, send_file, abort, session, redirect

from modules.uk.hardchecks import hard_pre_check as hardcheck_uk
from modules.uk.entity_check import check_entity_recall as recall_uk
from modules.uk.pdf import generate_pdf as pdf_uk

from modules.noise.hardchecks import hard_pre_check as hardcheck_noise
from modules.noise.pdf import generate_pdf as pdf_noise

from modules.uk.pre_checks import run_uk_pre_checks
from modules.noise.pre_checks import run_noise_pre_checks

# ─── Модуль 1 (Потребитель) ───
from modules.consumer.engine import process_consumer
from modules.consumer.pre_checks import run_consumer_pre_checks
from modules.consumer.pdf import generate_pdf as pdf_consumer
from modules.consumer.hardchecks import hard_pre_check as hardcheck_consumer, _is_legal_entity
from modules.consumer import configs as consumer_configs

from core.trace import build_trace

from core.name_declension import decline_fio, detect_gender
from core.phone_check import validate_phone, normalize_phone
from core.llm import call_alice_flash
from core import case_db
from core.labels import problem_type_label, doc_type_label
from core.address import format_address

from region.extractor import extract_region
from region.db_client import get_law_for_region


API_KEY = os.getenv("YANDEX_API_KEY", "")
FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")
SECRET_KEY = os.getenv("SECRET_KEY", "")

# --- Версии правил и шаблонов ---
RULES_DATE = "2026.09"
TEMPLATE_VERSION = "1.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("legal_mind")


LOG_DIR = Path("/opt/legal_mind/logs")
if not LOG_DIR.exists():
    LOG_DIR = Path(__file__).parent.parent / "logs"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass
EVENT_LOG = LOG_DIR / "requests.log"


def log_event(module: str, problem_len: int, stop_kind: str,
              retried: bool, pdf_ok: bool, extra: str = "") -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = (
        f"{ts} | {module:<5} | len={problem_len:<4} | "
        f"stop={stop_kind or '-':<14} | retry={'yes' if retried else 'no':<3} | "
        f"pdf={'ok' if pdf_ok else '-'}"
        f"{' | ' + extra if extra else ''}\n"
    )
    try:
        with open(EVENT_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError as e:
        log.warning("Не удалось записать event log: %s", e)


app = Flask(__name__)
app.secret_key = SECRET_KEY or "dev-insecure-key-change-me"

# ─── Jinja-фильтр: код → русское название ───
app.jinja_env.filters["problem_label"] = problem_type_label
app.jinja_env.filters["doc_label"] = doc_type_label


try:
    case_db.init_db()
    log.info("CASE DB инициализирована: %s", case_db.DB_PATH)
except Exception as e:
    log.error("Не удалось инициализировать CASE DB: %s", e)


# ─── Работа с session ───
_SESSION_KEY = "my_cases"
_MAX_CASES_IN_SESSION = 100
_SESSION_FORM_KEY = "last_form"


def _add_case_to_session(case_ref: str) -> None:
    """Добавляет case_ref в список моих дел в session."""
    cases = session.get(_SESSION_KEY, [])
    if case_ref in cases:
        cases.remove(case_ref)
    cases.insert(0, case_ref)  # новые сверху
    session[_SESSION_KEY] = cases[:_MAX_CASES_IN_SESSION]


def _get_my_cases() -> list[dict]:
    """Возвращает список моих дел из session."""
    refs = session.get(_SESSION_KEY, [])
    result = []
    for ref in refs:
        if len(ref) < 33 or ref[-33] != "-":
            continue
        case_uuid = ref[-32:]
        case_number = ref[:-33]
        case = case_db.get_case(case_number, case_uuid)
        if case is None:
            continue
        docs = case_db.get_documents(case_number)
        result.append({
            "case_number": case_number,
            "case_ref": ref,
            "problem_type": case["problem_type"],
            "jurisdiction": case.get("jurisdiction"),
            "created_at": case["created_at"],
            "documents_count": len(docs),
        })
    return result


def _save_form_to_session(form) -> None:
    """Сохраняет данные формы, чтобы показать их после возврата."""
    try:
        session[_SESSION_FORM_KEY] = {
            "problem_type":    form.get("problem_type", "uk"),
            "проблема":         form.get("проблема", ""),
            "адрес":            form.get("адрес", ""),
            "дата_начала":      form.get("дата_начала", ""),
            "обращались_ранее": form.get("обращались_ранее", ""),
            "фио":              form.get("фио", ""),
            "телефон":          form.get("телефон", ""),
            "organization":     form.get("organization", ""),
        }
    except Exception as e:
        log.warning("Не удалось сохранить форму в session: %s", e)


def _pop_saved_form():
    """Возвращает сохранённую форму и очищает session."""
    data = session.pop(_SESSION_FORM_KEY, None)
    if data is None:
        return None
    class _FormData(dict):
        def get(self, key, default=""):
            return dict.get(self, key, default) or default
    return _FormData(data)


def _parse_case_ref(case_ref: str) -> tuple[str, str] | None:
    """'LM-20260911-4821-<32hex>' → (number, uuid) или None."""
    if not case_ref or len(case_ref) < 33 or case_ref[-33] != "-":
        return None
    case_uuid = case_ref[-32:]
    case_number = case_ref[:-33]
    if not case_number.startswith("LM-"):
        return None
    return case_number, case_uuid


# ═══════════════════════════════════════════════════════════════
#  Промпты
# ═══════════════════════════════════════════════════════════════

ALLOWED_UK_NORMS = [
    "Статья 161 Жилищного кодекса РФ",
    "Постановление Правительства РФ от 13.08.2006 № 491",
    "Постановление Госстроя РФ от 27.09.2003 № 170",
]

SYSTEM_PROMPT_UK = """Ты — модуль нормализации данных для юридического сервиса. Твоя задача:
превратить неформальное описание проблемы от пользователя в строгую формулировку
для заявления в управляющую компанию (УК).

СТРОГИЕ ПРАВИЛА:
1. Не придумывай номера постановлений или пунктов, которых нет в списке ниже.
2. Не добавляй факты, которых пользователь не сообщал.
3. Не давай оценок, не обвиняй конкретных лиц, только фиксируй факт нарушения.
4. Тон — сухой, официальный, без эмоциональной окраски.
5. ОБЯЗАН сохранить все существенные обстоятельства: наличие детей, пожилых
   людей, инвалидов, угрозу имуществу, упоминание посторонних лиц, номер
   квартиры/подъезда/этажа, конкретные даты.
6. Конкретные объекты (мусор, грязь, снег, лифт, крыша, домофон, проводка,
   батарея) должны остаться в тексте.

ОСОБОЕ ПРАВИЛО ПРО ПОВТОРНОЕ ОБРАЩЕНИЕ:
- Если "обращались_ранее" = "нет" — верни РОВНО пустую строку.
- Если обращался — фразу с заглавной: "Ранее обращался(-ась) 05.03.2026, ответа не последовало."

РАЗРЕШЁННЫЕ ССЫЛКИ НА НОРМЫ (только эти):
- "Статья 161 Жилищного кодекса РФ"
- "Постановление Правительства РФ от 13.08.2006 № 491"
- "Постановление Госстроя РФ от 27.09.2003 № 170"

ФОРМАТ ВЫХОДА (строго JSON):
{
  "описание_проблемы_формальное": "...",
  "упоминание_повторного_обращения": "" или "Ранее обращался(-ась) 05.03.2026, ...",
  "применимые_нормы": [
     "Статья 161 Жилищного кодекса РФ",
     "Постановление Правительства РФ от 13.08.2006 № 491",
     "Постановление Госстроя РФ от 27.09.2003 № 170"
  ]
}"""

SYSTEM_PROMPT_NOISE = """Ты — модуль нормализации данных для юридического сервиса. Твоя задача:
превратить неформальное описание нарушения тишины в строгую формулировку
для заявления участковому уполномоченному полиции.

СТРОГИЕ ПРАВИЛА:
1. НЕ ссылайся на конкретные законы, статьи, постановления.
2. Не добавляй факты, которых пользователь не сообщал.
3. Не давай оценок, не обвиняй конкретных лиц.
4. Тон — сухой, официальный.
5. ОБЯЗАН сохранить: вид шума, время суток, длительность.

6. ВАЖНО ПРО КВАРТИРУ-ИСТОЧНИК:
   - Если пользователь пишет "соседи сверху" → "из квартиры, расположенной
     выше"
   - Если "соседи снизу" → "из квартиры, расположенной ниже"
   - Если "за стеной" → "из квартиры, расположенной за стеной"
   - Если "сосед из кв. 45" → указывай номер "45"
   - НОЛЬ подстановок номера квартиры ЗАЯВИТЕЛЯ как источника шума.

7. НЕ пиши адрес или номер квартиры заявителя в качестве места шума.
   Заявитель — пострадавшая сторона, а не источник.

ФОРМАТ ВЫХОДА (строго JSON):
{
  "описание_проблемы_формальное": "..."
}"""

CORRECTIVE_TEMPLATE = """Твой предыдущий ответ потерял существенные факты.

Исходное описание:
{problem}

Твой предыдущий ответ:
{previous}

Пропущены: {missing}.

Перепиши ответ заново, сохранив ВСЕ факты. Верни СТРОГО JSON того же формата."""


# ═══════════════════════════════════════════════════════════════
#  LLM
# ═══════════════════════════════════════════════════════════════

def _parse_llm_json(raw: str) -> dict:
    cleaned = (raw.strip()
               .removeprefix("```json").removeprefix("```")
               .removesuffix("```").strip())
    return json.loads(cleaned)


def _call_llm(instructions: str, user_input: str) -> dict:
    result = call_alice_flash(instructions, user_input, temperature=0.2, max_tokens=900)
    if "error" in result:
        return {"error": result["error"]}
    raw = result.get("text", "")
    try:
        parsed = _parse_llm_json(raw)
    except json.JSONDecodeError as e:
        return {"error": f"Не удалось распарсить JSON: {e}", "raw_response": raw}
    return {"parsed": parsed, "raw_response": raw}


# ═══════════════════════════════════════════════════════════════
#  Модуль 2 (УК)
# ═══════════════════════════════════════════════════════════════

def process_uk(user_data: dict) -> dict:
    hc = hardcheck_uk(user_data)
    if hc is not None:
        kind = "emergency" if hc["emergency"] else "hard_check"
        return {
            "kind": "stop", "reason": hc["stop_reason"],
            "emergency": hc["emergency"], "stop_kind": kind, "retried": False,
        }

    payload = {k: v for k, v in user_data.items() if k != "название"}
    user_msg = json.dumps(payload, ensure_ascii=False)

    a1 = _call_llm(SYSTEM_PROMPT_UK, user_msg)
    if "error" in a1:
        return {"kind": "error", "message": a1["error"], "retried": False}

    parsed = a1["parsed"]
    required = {"описание_проблемы_формальное", "упоминание_повторного_обращения", "применимые_нормы"}
    if required - set(parsed):
        return {"kind": "error", "message": "Модель вернула неполный JSON", "retried": False}
    if not isinstance(parsed["применимые_нормы"], list) or not set(parsed["применимые_нормы"]).issubset(set(ALLOWED_UK_NORMS)):
        return {"kind": "error", "message": "Модель использовала недопустимые нормы", "retried": False}

    recall = recall_uk(user_data.get("проблема", ""),
                       user_data.get("дата_начала", ""),
                       parsed["описание_проблемы_формальное"])
    retried = False
    if not recall["ok"]:
        retried = True
        missing = ", ".join(f"{m['kind']}:{m['value']}" for m in recall["missing"])
        corrective = CORRECTIVE_TEMPLATE.format(
            problem=user_data.get("проблема", ""),
            previous=parsed["описание_проблемы_формальное"],
            missing=missing,
        )
        a2 = _call_llm(SYSTEM_PROMPT_UK, corrective)
        if "error" not in a2:
            parsed = a2["parsed"]

    return {"kind": "ok", "parsed": parsed, "retried": retried, "stop_kind": None}


# ═══════════════════════════════════════════════════════════════
#  Модуль 3 (Шум)
# ═══════════════════════════════════════════════════════════════

def process_noise(user_data: dict) -> dict:
    hc = hardcheck_noise(user_data)
    if hc is not None:
        kind = "emergency" if hc["emergency"] else "hard_check"
        return {
            "kind": "stop", "reason": hc["stop_reason"],
            "emergency": hc["emergency"], "stop_kind": kind, "retried": False,
        }

    payload = {k: v for k, v in user_data.items() if k != "название"}
    user_msg = json.dumps(payload, ensure_ascii=False)

    a1 = _call_llm(SYSTEM_PROMPT_NOISE, user_msg)
    if "error" in a1:
        return {"kind": "error", "message": a1["error"], "retried": False}

    parsed = a1["parsed"]
    if "описание_проблемы_формальное" not in parsed:
        return {"kind": "error", "message": "Модель вернула неполный JSON", "retried": False}
    if not parsed["описание_проблемы_формальное"].strip():
        return {"kind": "error", "message": "Модель вернула пустое описание", "retried": False}

    address = user_data.get("адрес", "")
    region = extract_region(address)
    law_data = get_law_for_region(region) if region else None

    return {
        "kind": "ok",
        "parsed": parsed,
        "retried": False,
        "stop_kind": None,
        "region": region,
        "law_data": law_data,
    }


# ═══════════════════════════════════════════════════════════════
#  Модуль 1 (Потребитель)
# ═══════════════════════════════════════════════════════════════

def _get_consumer_config(scenario: str):
    """Возвращает CONFIG по коду сценария или None."""
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


def _resolve_consumer_scenario(user_data: dict) -> str:
    """Определяет сценарий: явный -> детектор -> defect."""
    from modules.consumer.scenario_detect import detect_scenario
    explicit = (user_data.get("scenario") or "").strip()
    if explicit in ("defect", "return14", "marketplace", "service"):
        return explicit
    detected = detect_scenario(user_data.get("проблема", ""))
    if detected:
        log.info("Сценарий consumer: %s", detected)
        return detected
    log.info("Сценарий consumer не определён, fallback defect")
    return "defect"


def process_consumer_module(user_data: dict, scenario: str) -> dict:
    """Hard-check + engine для consumer."""
    hc = hardcheck_consumer(user_data)
    if hc is not None:
        return {
            "kind": "stop",
            "reason": hc["stop_reason"],
            "emergency": hc.get("emergency", False),
            "stop_kind": "hard_check",
            "retried": False,
        }
    result = process_consumer(user_data, scenario)
    result["scenario"] = scenario
    return result


# ═══════════════════════════════════════════════════════════════
#  PDF
# ═══════════════════════════════════════════════════════════════

def _make_pdf_bytes(module: str, requisites: dict, normalized: dict) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name
    try:
        if module == "uk":
            pdf_uk(tmp_path, requisites, normalized)
        else:
            pdf_noise(tmp_path, requisites, normalized)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _make_pdf_response(pdf_bytes: bytes):
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="zayavlenie.pdf",
    )


def _build_trace_dict(problem_type: str, user_data: dict, result: dict) -> dict | None:
    """Собирает Legal Trace для DNA."""
    try:
        if problem_type == "uk":
            norms = result.get("parsed", {}).get("применимые_нормы") or []
            source = ""
        elif problem_type == "noise":
            ld = result.get("law_data") or {}
            norms = [ld["закон"]] if ld.get("закон") else []
            source = ld.get("url", "")
        else:
            norms = []
            source = ""

        trace = build_trace(
            problem_type=problem_type,
            problem_text=user_data.get("проблема", ""),
            norms=norms,
            source=source,
        )
        return trace.to_dict() if not trace.is_empty() else None
    except Exception as e:
        log.warning("build_trace упал: %s", e)
        return None


def _build_dna(problem_type: str, user_data: dict, result: dict, precheck=None) -> dict:
    dna = {
        "subject": None,
        "object": None,
        "event": None,
        "dates": {"начало": user_data.get("дата_начала") or None},
        "amount": None,
        "counterparty": None,
        "jurisdiction": result.get("region"),
        "demand": None,
        "evidence": None,
        "confidence": precheck.to_dict() if precheck else None,
        "trace": _build_trace_dict(problem_type, user_data, result),
    }

    if problem_type == "uk":
        dna["subject"] = "собственник/жилец"
        dna["object"] = "общее имущество МКД"
        dna["event"] = "ненадлежащее содержание"
        dna["counterparty"] = "управляющая компания"
        dna["demand"] = "устранение нарушения"
    elif problem_type == "noise":
        dna["subject"] = "жилец"
        dna["object"] = "тишина и покой"
        dna["event"] = "нарушение тишины"
        dna["counterparty"] = "сосед"
        dna["demand"] = "привлечь к ответственности"
        if result.get("law_data"):
            dna["trace"] = {
                "закон": result["law_data"].get("закон"),
                "источник": result["law_data"].get("url"),
                "версия_базы": result["law_data"].get("version"),
            }

    return dna


def _build_engine_version(problem_type: str, scenario: str = "") -> str:
    if problem_type == "uk":
        return "uk-01"
    if problem_type == "noise":
        return "noise-01"
    if problem_type == "consumer" and scenario:
        return f"consumer-{scenario}-01"
    return f"{problem_type}-01"


# ═══════════════════════════════════════════════════════════════
#  Маршруты
# ═══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    my_cases = _get_my_cases()
    my_cases_count = len(my_cases)
    valid_refs = [c["case_ref"] for c in my_cases]
    if valid_refs != session.get(_SESSION_KEY, []):
        session[_SESSION_KEY] = valid_refs
    saved_form = _pop_saved_form()
    return render_template("index.html",
                           my_cases_count=my_cases_count,
                           form_data=saved_form,
                           errors=None)


@app.route("/submit", methods=["POST"])
def submit():
    problem_type = request.form.get("problem_type", "uk")
    user_data = {
        "проблема": request.form.get("проблема", "").strip(),
        "адрес": request.form.get("адрес", "").strip(),
        "дата_начала": request.form.get("дата_начала", "").strip(),
        "обращались_ранее": request.form.get("обращались_ранее", "").strip() or "нет",
    }
    if problem_type == "consumer":
        user_data["продавец"] = request.form.get("продавец", "").strip()
        user_data["адрес_продавца"] = request.form.get("адрес_продавца", "").strip()
        user_data["ссылка_продавца"] = request.form.get("ссылка_продавца", "").strip()
        user_data["дата_покупки"] = request.form.get("дата_покупки", "").strip()

# ─── Собираем ВСЕ ошибки валидации сразу ───
    errors = []
    if not user_data["проблема"]:
        errors.append("Заполните описание проблемы")
    if not user_data["адрес"]:
        errors.append("Заполните адрес")
    if not request.form.get("фио", "").strip():
        errors.append("Заполните ФИО")
    if problem_type == "consumer":
        _seller = request.form.get("продавец", "").strip()
        _seller_addr = request.form.get("адрес_продавца", "").strip()
        _seller_link = request.form.get("ссылка_продавца", "").strip()

        if not _seller:
            errors.append("Заполните поле «Продавец / исполнитель»")
        elif _is_legal_entity(_seller):
            if not _seller_addr:
                errors.append(
                    "Заполните поле «Адрес продавца» — для ООО/ИП он обязателен "
                    "(есть в ЕГРЮЛ/ЕГРИП, чеке или на сайте)."
                )
        else:
            # Физлицо
            if not _seller_addr and not _seller_link:
                errors.append(
                    "Для продавца-физлица нужен хотя бы адрес ИЛИ ссылка "
                    "на профиль/объявление — без этого претензию некуда "
                    "отправить."
                )

    phone_raw = request.form.get("телефон", "").strip()
    if not phone_raw:
        errors.append("Заполните контактный телефон")
    else:
        phone_ok, phone_error = validate_phone(phone_raw)
        if not phone_ok:
            errors.append(phone_error)

    if errors:
        log_event(problem_type, len(user_data["проблема"]),
                  "form_errors", False, False)
        return render_template("index.html",
                               my_cases_count=len(_get_my_cases()),
                               form_data=request.form,
                               errors=errors)

    requisites = {
        "фио": decline_fio(request.form.get("фио", "").strip()),
        "адрес": format_address(user_data["адрес"]),
        "телефон": normalize_phone(phone_raw),
    }
    organization = request.form.get("organization", "").strip()

    log.info("problem_type=%s org=%r addr=%r", problem_type, organization, user_data["адрес"])

    consumer_cfg = None
    consumer_scenario = None
    if problem_type == "uk":
        requisites["ук_название"] = organization or "Управляющая компания"
        result = process_uk(user_data)
    elif problem_type == "consumer":
        consumer_scenario = _resolve_consumer_scenario(user_data)
        consumer_cfg = _get_consumer_config(consumer_scenario)
        requisites["продавец"] = user_data.get("продавец") or "Продавец"
        requisites["адрес_продавца"] = user_data.get("адрес_продавца") or ""
        requisites["ссылка_продавца"] = user_data.get("ссылка_продавца") or ""
        _fio_raw = request.form.get("фио", "").strip()
        requisites["пол"] = detect_gender(_fio_raw) or "masc"
        result = process_consumer_module(user_data, consumer_scenario)
    else:
        requisites["адресат"] = organization or "Начальнику ОВД по району"
        result = process_noise(user_data)

    if result["kind"] == "stop":
        log_event(problem_type, len(user_data["проблема"]),
                  result.get("stop_kind") or "hard_check", False, False)
        _save_form_to_session(request.form)

        # Перед обычным стопом попробуем pre-check
        if not result.get("emergency"):
            try:
                if problem_type == "uk":
                    precheck_on_stop = run_uk_pre_checks(user_data)
                elif problem_type == "consumer":
                    precheck_on_stop = run_consumer_pre_checks(user_data)
                else:
                    precheck_on_stop = run_noise_pre_checks(user_data, extras={})
                if precheck_on_stop.is_blocked and precheck_on_stop.known:
                    return render_template(
                        "pre_check_blocked.html",
                        known=precheck_on_stop.known,
                        missing_critical=precheck_on_stop.missing_critical,
                        missing_optional=precheck_on_stop.missing_optional,
                    )
            except Exception as e:
                log.warning("pre-check on stop failed: %s", e)
        return render_template("stop.html",
                               title="Документ не составлен",
                               reason=result["reason"],
                               emergency=result.get("emergency", False))

    if result["kind"] == "error":
        log.error("LLM error: %s", result["message"])
        log_event(problem_type, len(user_data["проблема"]),
                  "llm_error", result.get("retried", False), False)
        _save_form_to_session(request.form)
        return render_template("stop.html",
                               title="Техническая ошибка",
                               reason=f"Не удалось обработать запрос. Попробуйте позже. ({result['message'][:120]})",
                               emergency=False)

    parsed = result["parsed"]
    if problem_type == "uk":
        normalized = {
            "описание_проблемы_формальное": parsed["описание_проблемы_формальное"],
            "упоминание_повторного_обращения": parsed.get("упоминание_повторного_обращения", ""),
            "применимые_нормы": parsed.get("применимые_нормы") or ALLOWED_UK_NORMS,
            "engine_version": _build_engine_version(problem_type),
            "rules_date": RULES_DATE,
            "template_version": TEMPLATE_VERSION,
        }
        extra_log = ""
    elif problem_type == "consumer":
        normalized = {
            "описание_проблемы_формальное": parsed["описание_проблемы_формальное"],
            "требование": parsed.get("требование", ""),
            "применимые_нормы": parsed.get("применимые_нормы") or [],
            "engine_version": _build_engine_version(problem_type, consumer_scenario),
            "rules_date": RULES_DATE,
            "template_version": TEMPLATE_VERSION,
        }
        extra_log = f"scenario={consumer_scenario}"
    else:
        law_data = result.get("law_data")
        normalized = {
            "описание_проблемы_формальное": parsed["описание_проблемы_формальное"],
            "engine_version": _build_engine_version(problem_type),
            "rules_date": RULES_DATE,
            "template_version": TEMPLATE_VERSION,
        }
        if law_data:
            normalized["применимая_норма"] = law_data["закон"]
        region = result.get("region") or "?"
        law_status = "law=yes" if law_data else "law=no"
        extra_log = f"region={region} | {law_status}"

    # ─── Pre-checks (Confidence / UNKNOWN) ───
    if problem_type == "uk":
        precheck = run_uk_pre_checks(user_data)
    elif problem_type == "consumer":
        precheck = run_consumer_pre_checks(user_data)
    else:
        precheck = run_noise_pre_checks(
            user_data,
            extras={
                "region": result.get("region"),
                "law_data": result.get("law_data"),
            },
        )

    if precheck.is_blocked:
        log_event(
            problem_type,
            len(user_data["проблема"]),
            "precheck_blocked",
            result.get("retried", False),
            False,
        )
        _save_form_to_session(request.form)
        return render_template(
            "pre_check_blocked.html",
            known=precheck.known,
            missing_critical=precheck.missing_critical,
            missing_optional=precheck.missing_optional,
        )

    if problem_type == "consumer":
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name
        try:
            pdf_consumer(tmp_path, requisites, normalized, config=consumer_cfg)
            with open(tmp_path, "rb") as f:
                pdf_bytes = f.read()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    else:
        pdf_bytes = _make_pdf_bytes(problem_type, requisites, normalized)

    case_ref = None
    try:
        dna = _build_dna(problem_type, user_data, result, precheck)
        case_info = case_db.create_case(
            problem_type=problem_type,
            source_text=user_data["проблема"],
            user_data=user_data,
            dna=dna,
            engine_version=_build_engine_version(problem_type, consumer_scenario or ""),
            rules_version="2026.09",
            template_version="1.0",
        )
        case_db.add_document(
            case_number=case_info["case_number"],
            doc_type="zayavlenie",
            content=pdf_bytes,
            template_version="1.0",
            engine_version=_build_engine_version(problem_type, consumer_scenario or ""),
        )
        case_ref = f"{case_info['case_number']}-{case_info['case_uuid']}"
        _add_case_to_session(case_ref)
        log.info("CASE создан: %s", case_info["case_number"])
        log_event(problem_type, len(user_data["проблема"]),
                  None, result.get("retried", False), True,
                  extra_log + f" | case={case_info['case_number']}")
    except Exception as e:
        log.error("Не удалось сохранить CASE: %s", e)
        log_event(problem_type, len(user_data["проблема"]),
                  None, result.get("retried", False), True, extra_log)

    # Если CASE сохранён — редирект на карточку с авто-скачиванием PDF.
    # Если нет — отдаём PDF напрямую (fallback).
    if case_ref:
        return redirect(f"/case/{case_ref}?just_created=1")

    return _make_pdf_response(pdf_bytes)


@app.route("/my")
def my_cases():
    """Список моих дел из session."""
    cases = _get_my_cases()
    return render_template("my.html", cases=cases)


@app.route("/case/<case_ref>")
def view_case(case_ref: str):
    parsed = _parse_case_ref(case_ref)
    if parsed is None:
        abort(404)
    case_number, case_uuid = parsed

    case = case_db.get_case(case_number, case_uuid)
    if case is None:
        abort(404)

    documents = case_db.get_documents(case_number)
    just_created = request.args.get("just_created") == "1"

    return render_template(
        "case.html",
        case=case,
        documents=documents,
        case_ref=case_ref,
        just_created=just_created,
    )


@app.route("/case/<case_ref>/pdf/<int:doc_id>")
def download_case_pdf(case_ref: str, doc_id: int):
    parsed = _parse_case_ref(case_ref)
    if parsed is None:
        abort(404)
    case_number, case_uuid = parsed

    case = case_db.get_case(case_number, case_uuid)
    if case is None:
        abort(404)

    content = case_db.get_document_content(doc_id)
    if content is None:
        abort(404)

    case_db.add_event(case_number, "viewed", {"doc_id": doc_id})

    return send_file(
        io.BytesIO(content),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{case_number}.pdf",
    )


@app.route("/health")
def health():
    try:
        st = case_db.stats()
        cases_total = st.get("total", 0)
    except Exception:
        cases_total = -1
    return {
        "status": "ok",
        "llm_provider": "alice-ai-flash",
        "llm_configured": bool(API_KEY and FOLDER_ID),
        "cases_total": cases_total,
    }


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)

