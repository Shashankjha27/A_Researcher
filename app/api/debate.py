from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config.settings import resolve_llm_config
from app.llm.client import get_llm_call
from app.pipeline.debate import run_debate
from app.store.doc_store import DocStore

router = APIRouter(tags=["debate"])


class DebateRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None


@router.post("/claims/{claim_id}/debate")
def run_claim_debate(
    claim_id: str,
    request: DebateRequest | None = None,
) -> dict[str, Any]:
    store = DocStore()

    claim = store.get("claims", claim_id)

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail=f"Claim not found: {claim_id}",
        )

    provider = request.provider if request else None
    model = request.model if request else None
    api_key = request.api_key if request else None

    try:
        config = resolve_llm_config(provider, model, api_key)
        llm_call = get_llm_call(
            provider=provider,
            model=model,
            api_key=api_key,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    evidence_texts = [
        item.get("text", "")
        for item in (claim.supporting_evidence or [])
        if isinstance(item, dict)
    ]

    try:
        record = run_debate(
            llm_call=llm_call,
            claim_id=claim.claim_id,
            paper_id=claim.paper_id,
            claim_text=claim.claim_text,
            evidence_texts=[text for text in evidence_texts if text],
            model_label=f"{config.provider}/{config.model}",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM call failed during debate: {exc}",
        ) from exc

    store.save("debates", record)

    return record.model_dump(mode="json")


@router.get("/claims/{claim_id}/debate")
def get_claim_debate(claim_id: str) -> dict[str, Any]:
    store = DocStore()

    debates = store.query("debates", claim_id=claim_id)

    if not debates:
        raise HTTPException(
            status_code=404,
            detail=f"No debate found for claim: {claim_id}",
        )

    latest = max(debates, key=lambda record: record.created_at)

    return latest.model_dump(mode="json")
