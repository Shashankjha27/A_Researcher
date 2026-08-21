from __future__ import annotations

import os
from collections.abc import Callable

from litellm import completion
from litellm.exceptions import Timeout as LiteLLMTimeout

from app.config import resolve_llm_config
from config import OLLAMA_BASE_URL

Provider = Callable[[str], str]

DEFAULT_LLM_TIMEOUT_S = int(os.environ.get("AR_LLM_TIMEOUT_S", "120"))
DEFAULT_TEMPERATURE = float(os.environ.get("AR_LLM_TEMPERATURE", "0.2"))
DEFAULT_MAX_TOKENS = int(os.environ.get("AR_LLM_MAX_TOKENS", "1024"))
DEFAULT_NUM_CTX = int(os.environ.get("AR_LLM_NUM_CTX", "8192"))


class LLMCallError(RuntimeError):
    """Raised when an LLM call fails or times out; message is user-facing."""


def _build_model_id(provider: str, model: str) -> str:
    if provider == "ollama":
        return f"ollama/{model}"
    return f"{provider}/{model}"


def get_llm_call(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    json_mode: bool = False,
) -> Provider:
    config = resolve_llm_config(provider, model, api_key)

    if not config.model:
        raise ValueError(
            "No LLM model configured. Set a provider and model in "
            "Settings (or pass provider/model explicitly)."
        )

    model_id = _build_model_id(config.provider, config.model)

    def call(prompt: str) -> str:
        kwargs: dict = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "timeout": DEFAULT_LLM_TIMEOUT_S,
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS,
        }
        if config.provider == "ollama":
            kwargs["api_base"] = OLLAMA_BASE_URL
            extra_body: dict = {
                "options": {"num_ctx": DEFAULT_NUM_CTX},
            }
            if json_mode:
                extra_body["format"] = "json"
            kwargs["extra_body"] = extra_body
        elif config.api_key:
            kwargs["api_key"] = config.api_key
        try:
            response = completion(**kwargs)
        except LiteLLMTimeout as exc:
            raise LLMCallError(
                f"LLM call timed out after {DEFAULT_LLM_TIMEOUT_S}s "
                f"({model_id}). Check that the provider is reachable, "
                "then retry."
            ) from exc
        except Exception as exc:
            raise LLMCallError(
                f"LLM call failed ({model_id}): {exc}"
            ) from exc
        return response.choices[0].message.content

    return call
