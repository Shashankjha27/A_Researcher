from __future__ import annotations

import os
from collections.abc import Callable

import httpx

from config import (
    CLAUDE_MODEL,
    GEMINI_MODEL,
    LLM_MODEL,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OPENAI_MODEL,
)

_TIMEOUT = 600

Provider = Callable[[str], str]


def _env(name: str) -> str:
    value = os.environ.get(name)

    if not value:
        raise RuntimeError(f"{name} not set; add it to .env")

    return value


def _post(
    url: str,
    *,
    json: dict,
    headers: dict | None = None,
    params: dict | None = None,
) -> dict:
    response = httpx.post(
        url,
        json=json,
        headers=headers,
        params=params,
        timeout=_TIMEOUT,
    )

    response.raise_for_status()

    return response.json()


def _ollama(prompt: str) -> str:
    data = _post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False,
        },
    )

    return data["response"]


def _openai(prompt: str) -> str:
    data = _post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {_env('OPENAI_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        },
    )

    return data["choices"][0]["message"]["content"]


def _gemini(prompt: str) -> str:
    data = _post(
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent",
        headers={
            "x-goog-api-key": _env("GEMINI_API_KEY"),
            "Content-Type": "application/json",
        },
        json={
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt,
                        }
                    ]
                }
            ],
        },
    )

    return data["candidates"][0]["content"]["parts"][0]["text"]


def _claude(prompt: str) -> str:
    data = _post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": _env("ANTHROPIC_API_KEY"),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        },
    )

    return data["content"][0]["text"]


_PROVIDERS: dict[str, Provider] = {
    "ollama": _ollama,
    "openai": _openai,
    "gemini": _gemini,
    "claude": _claude,
}


def get_llm_call() -> Provider:
    provider = LLM_PROVIDER.lower().strip()

    try:
        return _PROVIDERS[provider]
    except KeyError:
        supported = ", ".join(sorted(_PROVIDERS))
        raise ValueError(
            f"unknown LLM provider: {LLM_PROVIDER!r}. "
            f"Supported providers: {supported}"
        ) from None