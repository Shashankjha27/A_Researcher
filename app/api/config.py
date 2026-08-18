from fastapi import APIRouter, Header

from app.config import (
    LLMConfigResponse,
    clear_settings,
    get_config_response,
    resolve_llm_config,
    save_settings,
)
from app.config.schema import LLMConfigRequest

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=LLMConfigResponse)
def get_config() -> LLMConfigResponse:
    return get_config_response()


@router.post("", response_model=LLMConfigResponse)
def post_config(request: LLMConfigRequest) -> LLMConfigResponse:
    return save_settings(request)


@router.delete("")
def delete_config() -> dict:
    clear_settings()
    return {"status": "cleared"}


@router.get("/resolve", response_model=LLMConfigResponse)
def resolve_config(
    x_llm_provider: str | None = Header(default=None, alias="X-LLM-Provider"),
    x_llm_model: str | None = Header(default=None, alias="X-LLM-Model"),
    x_llm_key: str | None = Header(default=None, alias="X-LLM-Key"),
) -> LLMConfigResponse:
    config = resolve_llm_config(x_llm_provider, x_llm_model, x_llm_key)
    return LLMConfigResponse(
        provider=config.provider,
        model=config.model,
        has_key=config.api_key is not None,
        configured=True,
    )
