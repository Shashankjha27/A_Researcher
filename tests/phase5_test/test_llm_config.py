import pytest

from app.config import settings as settings_module
from app.config.schema import LLMConfig
from app.llm import client as llm_client


def test_resolve_uses_saved_ollama_settings_without_key(monkeypatch):
    saved = LLMConfig(
        provider="ollama",
        model="llama3.2:latest",
        api_key=None,
    )

    monkeypatch.setattr(settings_module, "get_settings", lambda: saved)

    config = settings_module.resolve_llm_config()

    assert config.provider == "ollama"
    assert config.model == "llama3.2:latest"
    assert config.api_key is None


def test_resolve_uses_saved_keyed_settings(monkeypatch):
    saved = LLMConfig(
        provider="openai",
        model="gpt-4o-mini",
        api_key="sk-test",
    )

    monkeypatch.setattr(settings_module, "get_settings", lambda: saved)

    config = settings_module.resolve_llm_config()

    assert config.provider == "openai"
    assert config.model == "gpt-4o-mini"
    assert config.api_key == "sk-test"


def test_resolve_falls_back_to_default_ollama(monkeypatch):
    monkeypatch.setattr(settings_module, "get_settings", lambda: None)

    config = settings_module.resolve_llm_config()

    assert config.provider == "ollama"


def test_explicit_ollama_override_beats_saved_settings(monkeypatch):
    saved = LLMConfig(
        provider="gemini",
        model="gemini-3-flash-preview",
        api_key="saved-key",
    )

    monkeypatch.setattr(settings_module, "get_settings", lambda: saved)

    config = settings_module.resolve_llm_config(
        header_provider="ollama",
        header_model="llama3.2:latest",
    )

    assert config.provider == "ollama"
    assert config.model == "llama3.2:latest"
    assert config.api_key is None


def test_get_llm_call_raises_clear_error_without_model(monkeypatch):
    monkeypatch.setattr(
        llm_client,
        "resolve_llm_config",
        lambda *args, **kwargs: LLMConfig(
            provider="ollama",
            model="",
            api_key=None,
        ),
    )

    with pytest.raises(ValueError, match="No LLM model configured"):
        llm_client.get_llm_call()


def test_llm_timeout_raises_friendly_error(monkeypatch):
    from litellm.exceptions import Timeout as LiteLLMTimeout

    monkeypatch.setattr(
        llm_client,
        "resolve_llm_config",
        lambda *args, **kwargs: LLMConfig(
            provider="ollama",
            model="llama3.2:latest",
            api_key=None,
        ),
    )

    def _hang(**kwargs):
        raise LiteLLMTimeout(message="timed out", model="ollama/llama3.2:latest", llm_provider="ollama")

    monkeypatch.setattr(llm_client, "completion", _hang)

    call = llm_client.get_llm_call()

    with pytest.raises(llm_client.LLMCallError, match="timed out after"):
        call("extract claims")


def test_llm_failure_wrapped_with_model_id(monkeypatch):
    monkeypatch.setattr(
        llm_client,
        "resolve_llm_config",
        lambda *args, **kwargs: LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key="sk-test",
        ),
    )

    def _boom(**kwargs):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(llm_client, "completion", _boom)

    call = llm_client.get_llm_call()

    with pytest.raises(
        llm_client.LLMCallError, match="openai/gpt-4o-mini"
    ):
        call("extract claims")


def test_completion_receives_timeout_kwarg(monkeypatch):
    captured: dict = {}

    monkeypatch.setattr(
        llm_client,
        "resolve_llm_config",
        lambda *args, **kwargs: LLMConfig(
            provider="ollama",
            model="llama3.2:latest",
            api_key=None,
        ),
    )

    def _fake_completion(**kwargs):
        captured.update(kwargs)

        class _Msg:
            content = "ok"

        class _Choice:
            message = _Msg()

        class _Resp:
            def __init__(self) -> None:
                self.choices = [_Choice()]

        return _Resp()

    monkeypatch.setattr(llm_client, "completion", _fake_completion)

    call = llm_client.get_llm_call()
    assert call("hello") == "ok"
    assert captured["timeout"] == llm_client.DEFAULT_LLM_TIMEOUT_S
