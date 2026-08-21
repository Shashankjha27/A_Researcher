from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import keyring

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

_SERVICE_NAME = "a_researcher"
_KEY_NAME = "settings"
_MIGRATION_DONE_KEY = "migrated_from_json"


def _migrate_from_json_if_needed() -> None:
    """One-time migration: read encrypted settings.json, store in OS keychain, delete file."""
    path = _settings_path()

    if not path.exists():
        return

    already_migrated = keyring.get_password(_SERVICE_NAME, _MIGRATION_DONE_KEY)
    if already_migrated:
        return

    try:
        from base64 import urlsafe_b64decode, urlsafe_b64encode
        from hashlib import pbkdf2_hmac

        from cryptography.fernet import Fernet, InvalidToken

        data = json.loads(path.read_text(encoding="utf-8"))
        encrypted_key = data.get("api_key")
        api_key = None

        if encrypted_key:
            node_name = os.uname().nodename
            try:
                username = os.getlogin()
            except OSError:
                username = os.environ.get("USER", "default-user")

            raw = pbkdf2_hmac("sha256", node_name.encode(), username.encode(), 100_000)
            key = urlsafe_b64decode(raw[:32])[:32]

            try:
                fernet = Fernet(urlsafe_b64encode(key))
                api_key = fernet.decrypt(encrypted_key.encode()).decode()
            except InvalidToken:
                logger.warning(
                    "failed to decrypt api_key during migration, skipping key"
                )
                api_key = None

        _save_to_keychain(
            data.get("provider", "ollama"),
            data.get("model", ""),
            api_key,
        )

        keyring.set_password(_SERVICE_NAME, _MIGRATION_DONE_KEY, "true")

        path.unlink()
        logger.info("migrated settings from settings.json to OS keychain")

    except (json.JSONDecodeError, KeyError, TypeError, OSError):
        logger.warning(
            "failed to migrate settings.json to keychain, leaving file in place"
        )


def _save_to_keychain(provider: str, model: str, api_key: str | None) -> None:
    keyring.set_password(
        _SERVICE_NAME,
        _KEY_NAME,
        json.dumps(
            {
                "provider": provider,
                "model": model,
                "api_key": api_key,
            }
        ),
    )


def _load_from_keychain() -> dict | None:
    raw = keyring.get_password(_SERVICE_NAME, _KEY_NAME)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def get_settings() -> LLMConfig | None:
    _migrate_from_json_if_needed()

    data = _load_from_keychain()
    if data is None:
        return None

    return LLMConfig(
        provider=data.get("provider", "ollama"),
        model=data.get("model", ""),
        api_key=data.get("api_key"),
    )


def save_settings(
    request: LLMConfigRequest,
) -> LLMConfigResponse:
    _migrate_from_json_if_needed()

    _save_to_keychain(
        request.provider,
        request.model,
        request.api_key,
    )

    return LLMConfigResponse(
        provider=request.provider,
        model=request.model,
        has_key=bool(request.api_key),
        configured=True,
    )


def clear_settings() -> None:
    try:
        keyring.delete_password(_SERVICE_NAME, _KEY_NAME)
    except keyring.errors.PasswordDeleteError:
        pass


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


def _settings_path() -> Path:
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    return DATA_OUT / "settings.json"


def resolve_llm_config(
    header_provider: str | None = None,
    header_model: str | None = None,
    header_key: str | None = None,
) -> LLMConfig:
    # 1. Request headers have highest priority. Local providers (ollama)
    #    do not need an API key, so an explicit ollama override is valid
    #    without one.
    if header_provider and (
        header_key or header_provider == "ollama"
    ):
        return LLMConfig(
            provider=header_provider,
            model=header_model or "",
            api_key=header_key,
        )

    # 2. Use saved application settings. Local providers (ollama) do not
    #    need an API key, so saved settings are valid without one.
    settings = get_settings()

    if settings and (
        settings.provider == "ollama" or settings.api_key
    ):
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
