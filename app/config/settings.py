
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.config.schema import (
    LLMConfig,
    LLMConfigRequest,
    LLMConfigResponse,
)
from config import (
    CLAUDE_MODEL,
    DATA_OUT,
    GEMINI_MODEL,
    LLM_MODEL,
    LLM_PROVIDER,
    OPENAI_MODEL,
)

logger = logging.getLogger(__name__)

_FERNET: Fernet | None = None


def _get_fernet() -> Fernet:
    global _FERNET

    if _FERNET is not None:
        return _FERNET

    node_name = os.uname().nodename

    try:
        username = os.getlogin()
    except OSError:
        username = os.environ.get("USER", "default-user")

    raw = hashlib.pbkdf2_hmac(
        "sha256",
        node_name.encode(),
        username.encode(),
        100_000,
    )

    key = base64.urlsafe_b64encode(raw[:32])

    _FERNET = Fernet(key)

    return _FERNET


def _encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(
        plaintext.encode()
    ).decode()


def _decrypt(ciphertext: str) -> str:
    return _get_fernet().decrypt(
        ciphertext.encode()
    ).decode()


def _settings_path() -> Path:
    DATA_OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    return DATA_OUT / "settings.json"


def get_settings() -> LLMConfig | None:
    path = _settings_path()

    if not path.exists():
        return None

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )

        api_key = None

        encrypted_key = data.get("api_key")

        if encrypted_key:
            try:
                api_key = _decrypt(encrypted_key)
            except InvalidToken:
                logger.warning(
                    "failed to decrypt api_key in settings.json"
                )
                api_key = None

        return LLMConfig(
            provider=data.get(
                "provider",
                "ollama",
            ),
            model=data.get(
                "model",
                "",
            ),
            api_key=api_key,
        )

    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
    ):
        logger.warning(
            "corrupt settings.json, ignoring"
        )

        return None


def save_settings(
    request: LLMConfigRequest,
) -> LLMConfigResponse:
    path = _settings_path()

    encrypted_key = None

    if request.api_key:
        encrypted_key = _encrypt(
            request.api_key
        )

    data = {
        "provider": request.provider,
        "model": request.model,
        "api_key": encrypted_key,
    }

    path.write_text(
        json.dumps(
            data,
            indent=2,
        ),
        encoding="utf-8",
    )

    return LLMConfigResponse(
        provider=request.provider,
        model=request.model,
        has_key=bool(request.api_key),
        configured=True,
    )


def clear_settings() -> None:
    path = _settings_path()

    if path.exists():
        path.unlink()


def get_config_response() -> LLMConfigResponse:
    settings = get_settings()

    if settings is None:
        return LLMConfigResponse(
            configured=False,
        )

    return LLMConfigResponse(
        provider=settings.provider,
        model=settings.model,
        has_key=settings.api_key is not None,
        configured=True,
    )


def resolve_llm_config(
    header_provider: str | None = None,
    header_model: str | None = None,
    header_key: str | None = None,
) -> LLMConfig:
    # 1. Request headers have highest priority.
    if header_provider and header_key:
        return LLMConfig(
            provider=header_provider,
            model=header_model or "",
            api_key=header_key,
        )

    # 2. Use saved application settings.
    settings = get_settings()

    if settings and settings.api_key:
        return settings

    # 3. Fall back to environment configuration.
    env_provider = LLM_PROVIDER

    if env_provider and env_provider != "ollama":
        env_key = os.environ.get(
            f"{env_provider.upper()}_API_KEY",
            "",
        )

        if env_key:
            return LLMConfig(
                provider=env_provider,
                model=_env_model_for(env_provider),
                api_key=env_key,
            )

    # 4. Default to local Ollama.
    return LLMConfig(
        provider="ollama",
        model=LLM_MODEL or "",
        api_key=None,
    )


def _env_model_for(provider: str) -> str:
    if provider == "openai":
        return OPENAI_MODEL

    if provider == "gemini":
        return GEMINI_MODEL

    if provider == "claude":
        return CLAUDE_MODEL

    return ""
