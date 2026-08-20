from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.llm.client import get_llm_call
from app.pipeline.extract import extract_claims_from_chunk
from app.store.doc_store import DocStore

router = APIRouter(tags=["extraction"])


class ExtractRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None


@router.post("/extract/{paper_id}")
def extract(
    paper_id: str,
    request: ExtractRequest | None = None,
) -> dict[str, Any]:
    store = DocStore()

    paper = store.get("papers", paper_id)

    if paper is None:
        raise HTTPException(
            status_code=404,
            detail=f"Paper not found: {paper_id}",
        )

    provider = request.provider if request else None
    model = request.model if request else None
    api_key = request.api_key if request else None

    llm_call = get_llm_call(
        provider=provider,
        model=model,
        api_key=api_key,
    )

    claims = []

    for block in paper.blocks:
        block_claims = extract_claims_from_chunk(
            llm_call=llm_call,
            chunk_text=block.text,
            paper_id=paper.paper_id,
            section=block.section,
            chunk_start_offset=block.start_offset,
        )
        claims.extend(block_claims)

    for claim in claims:
        store.save("claims", claim)

    return {
        "paper_id": paper_id,
        "claims": [c.model_dump() for c in claims],
    }
