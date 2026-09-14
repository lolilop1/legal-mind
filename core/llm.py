"""Alice AI client wrapper for Yandex AI Studio.

Provides:
- call_alice_flash(instructions, user_input) — cheap, fast, for normalization
- call_alice_pro(instructions, user_input)   — flagship, for RAG extraction

Uses OpenAI-compatible Responses API.
"""

import logging
import os
import time

import openai
from dotenv import load_dotenv


# Загружаем .env из web/ явно — работает независимо от cwd
from pathlib import Path as _Path
_web_env = _Path(__file__).resolve().parent.parent / "web" / ".env"
load_dotenv(dotenv_path=_web_env if _web_env.exists() else None)

FOLDER = os.getenv("YANDEX_FOLDER_ID", "")
API_KEY = os.getenv("YANDEX_API_KEY", "")

BASE_URL = "https://ai.api.cloud.yandex.net/v1"

log = logging.getLogger("legal_mind")

# ─── Retry настройки ───
MAX_RETRIES = 3
RETRY_BACKOFF = (1.0, 2.0, 4.0)

_NO_RETRY_ERRORS = (
    openai.AuthenticationError,
    openai.BadRequestError,
    openai.NotFoundError,
    openai.PermissionDeniedError,
)

_RETRY_ERRORS = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)

_client = None


def _get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        _client = openai.OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
            project=FOLDER,
        )
    return _client


def _call(model_short: str, instructions: str, user_input: str,
          temperature: float = 0.2, max_tokens: int = 1500) -> dict:
    """Общий вызов. model_short: 'aliceai-llm' или 'aliceai-llm-flash'."""
    if not FOLDER or not API_KEY:
        return {"error": "Не настроены YANDEX_API_KEY / YANDEX_FOLDER_ID"}

    client = _get_client()
    model_uri = f"gpt://{FOLDER}/{model_short}/latest"

    response = None
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = client.responses.create(
                model=model_uri,
                temperature=temperature,
                instructions=instructions,
                input=user_input,
                max_output_tokens=max_tokens,
            )
            if attempt > 0:
                log.info("Alice AI (%s): успех с попытки %d", model_short, attempt + 1)
            break
        except _NO_RETRY_ERRORS as e:
            log.warning("Alice AI (%s) client error: %s", model_short, e)
            return {"error": f"{type(e).__name__}: {e}"}
        except _RETRY_ERRORS as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[attempt]
                log.warning(
                    "Alice AI (%s) retry %d/%d через %.1f с: %s",
                    model_short, attempt + 1, MAX_RETRIES, wait, e,
                )
                time.sleep(wait)
            else:
                log.warning("Alice AI (%s) все %d попыток провалились: %s",
                            model_short, MAX_RETRIES, e)
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[attempt]
                log.warning(
                    "Alice AI (%s) unknown retry %d/%d через %.1f с: %s",
                    model_short, attempt + 1, MAX_RETRIES, wait, e,
                )
                time.sleep(wait)
            else:
                log.warning("Alice AI (%s) все попытки: %s", model_short, e)

    if response is None:
        return {"error": f"{type(last_error).__name__}: {last_error}"}

    try:
        text = response.output_text
        usage = getattr(response, "usage", None)
        result = {"text": text}
        if usage:
            result["input_tokens"] = getattr(usage, "input_tokens", 0)
            result["output_tokens"] = getattr(usage, "output_tokens", 0)
        return result
    except Exception as e:
        log.warning("Alice AI parse error: %s", e)
        return {"error": f"parse: {e}", "raw": str(response)[:500]}


def call_alice_flash(instructions: str, user_input: str,
                     temperature: float = 0.2, max_tokens: int = 1500) -> dict:
    """Дешёвая быстрая модель. Для нормализации текста."""
    return _call("aliceai-llm-flash", instructions, user_input,
                 temperature, max_tokens)


def call_alice_pro(instructions: str, user_input: str,
                   temperature: float = 0.0, max_tokens: int = 1500) -> dict:
    """Флагманская модель. Для RAG и сложных задач."""
    return _call("aliceai-llm", instructions, user_input,
                 temperature, max_tokens)