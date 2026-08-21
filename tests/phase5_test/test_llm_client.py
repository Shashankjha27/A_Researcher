from types import SimpleNamespace

from app.config.schema import LLMConfig
from app.llm import client as llm_client


def _fake_response(content: str):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            ),
        ],
    )


def _patch(monkeypatch, provider: str, captured: dict):
    monkeypatch.setattr(
        llm_client,
        "resolve_llm_config",
        lambda *args, **kwargs: LLMConfig(
            provider=provider,
            model="test-model",
            api_key="key" if provider != "ollama" else None,
        ),
    )

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _fake_response("[]")

    monkeypatch.setattr(llm_client, "completion", fake_completion)


def test_ollama_json_mode_sends_runtime_options(monkeypatch):
    captured: dict = {}
    _patch(monkeypatch, "ollama", captured)

    call = llm_client.get_llm_call(json_mode=True)
    output = call("extract claims")

    assert output == "[]"
    assert captured["temperature"] == llm_client.DEFAULT_TEMPERATURE
    assert captured["max_tokens"] == llm_client.DEFAULT_MAX_TOKENS
    assert captured["extra_body"]["format"] == "json"
    assert (
        captured["extra_body"]["options"]["num_ctx"]
        == llm_client.DEFAULT_NUM_CTX
    )


def test_ollama_without_json_mode_keeps_prose_output(monkeypatch):
    captured: dict = {}
    _patch(monkeypatch, "ollama", captured)

    call = llm_client.get_llm_call()
    call("argue a point")

    assert "format" not in captured["extra_body"]
    assert (
        captured["extra_body"]["options"]["num_ctx"]
        == llm_client.DEFAULT_NUM_CTX
    )


def test_non_ollama_provider_skips_extra_body(monkeypatch):
    captured: dict = {}
    _patch(monkeypatch, "openai", captured)

    call = llm_client.get_llm_call(json_mode=True)
    call("extract claims")

    assert "extra_body" not in captured
    assert captured["temperature"] == llm_client.DEFAULT_TEMPERATURE
    assert captured["max_tokens"] == llm_client.DEFAULT_MAX_TOKENS
