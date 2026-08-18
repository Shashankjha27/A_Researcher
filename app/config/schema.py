from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LLMConfigRequest(BaseModel):
    provider: Literal["openai", "gemini", "claude", "ollama"]
    model: str
    api_key: str | None = None


class LLMConfigResponse(BaseModel):
    provider: str | None = None
    model: str | None = None
    has_key: bool = False
    configured: bool = False


class LLMConfig(BaseModel):
    provider: str = "ollama"
    model: str = ""
    api_key: str | None = None
