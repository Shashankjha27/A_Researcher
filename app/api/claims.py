from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.store.doc_store import DocStore

router = APIRouter(tags=["claims"])


@router.get("/claims")
def list_claims() -> list[dict[str, Any]]:
    store = DocStore()

    latest: dict[str, Any] = {}

    for claim in store.all("claims"):
        latest[claim.claim_id] = claim

    return [
        {
            "claim_id": claim.claim_id,
            "paper_id": claim.paper_id,
            "claim_text": claim.claim_text,
            "verdict": (
                claim.verdict.value if claim.verdict is not None else None
            ),
        }
        for claim in latest.values()
    ]


@router.get("/claims/{claim_id}")
def get_claim(claim_id: str) -> dict[str, Any]:
    store = DocStore()

    claim = store.get("claims", claim_id)

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail=f"Claim not found: {claim_id}",
        )

    verdicts_a = store.query(
        "pair_verdicts",
        claim_id_a=claim_id,
    )
    verdicts_b = store.query(
        "pair_verdicts",
        claim_id_b=claim_id,
    )

    linked_verdicts = [
        v.model_dump() for v in verdicts_a + verdicts_b
    ]

    return {
        "claim": claim.model_dump(),
        "linked_verdicts": linked_verdicts,
    }
