from __future__ import annotations

from collections.abc import Callable

from litellm import completion

from app.config import resolve_llm_config
from config import OLLAMA_BASE_URL

Provider = Callable[[str], str]


def _build_model_id(provider: str, model: str) -> str:
    if provider == "ollama":
        return f"ollama/{model}"
    return f"{provider}/{model}"


def get_llm_call(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> Provider:
    config = resolve_llm_config(provider, model, api_key)
    model_id = _build_model_id(config.provider, config.model)

    def call(prompt: str) -> str:
        kwargs: dict = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
        }
        if config.provider == "ollama":
            kwargs["api_base"] = OLLAMA_BASE_URL
        elif config.api_key:
            kwargs["api_key"] = config.api_key
        response = completion(**kwargs)
        return response.choices[0].message.content

    return call
