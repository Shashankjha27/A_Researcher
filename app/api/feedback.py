from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas import FlagReview, VerdictOverride
from app.scoring.verdict import Verdict
from app.store.doc_store import DocStore

router = APIRouter(tags=["feedback"])


class OverrideRequest(BaseModel):
    verdict: Verdict
    note: str | None = None


class FlagReviewRequest(BaseModel):
    accepted: bool


def _latest_by(
    records: list[Any],
    id_field: str,
) -> dict[str, Any]:
    latest: dict[str, Any] = {}

    for record in records:
        latest[getattr(record, id_field)] = record

    return latest


@router.post("/claims/{claim_id}/override")
def override_verdict(
    claim_id: str,
    request: OverrideRequest,
) -> dict[str, Any]:
    store = DocStore()

    claim = store.get("claims", claim_id)

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail=f"Claim not found: {claim_id}",
        )

    record = VerdictOverride(
        override_id=f"ov_{uuid.uuid4().hex[:12]}",
        claim_id=claim.claim_id,
        paper_id=claim.paper_id,
        original_verdict=claim.verdict,
        overridden_verdict=request.verdict,
        note=request.note or None,
        created_at=datetime.now(timezone.utc),
    )

    store.save("verdict_overrides", record)

    return record.model_dump(mode="json")


@router.get("/claims/{claim_id}/override")
def get_override(claim_id: str) -> dict[str, Any]:
    overrides = DocStore().query(
        "verdict_overrides",
        claim_id=claim_id,
    )

    if not overrides:
        raise HTTPException(
            status_code=404,
            detail=f"No override found for claim: {claim_id}",
        )

    latest = max(overrides, key=lambda record: record.created_at)

    return latest.model_dump(mode="json")


@router.get("/papers/{paper_id}/overrides")
def list_paper_overrides(paper_id: str) -> list[dict[str, Any]]:
    overrides = DocStore().query(
        "verdict_overrides",
        paper_id=paper_id,
    )

    latest = _latest_by(overrides, "claim_id")

    return [
        record.model_dump(mode="json")
        for record in sorted(
            latest.values(),
            key=lambda record: record.created_at,
        )
    ]


@router.post("/flags/{flag_id}/review")
def review_flag(
    flag_id: str,
    request: FlagReviewRequest,
) -> dict[str, Any]:
    store = DocStore()

    flag = store.get("flags", flag_id)

    if flag is None:
        raise HTTPException(
            status_code=404,
            detail=f"Flag not found: {flag_id}",
        )

    record = FlagReview(
        review_id=f"rv_{uuid.uuid4().hex[:12]}",
        flag_id=flag.flag_id,
        claim_id=flag.claim_id,
        accepted=request.accepted,
        created_at=datetime.now(timezone.utc),
    )

    store.save("flag_reviews", record)

    return record.model_dump(mode="json")


@router.get("/stats/agreement")
def agreement_stats() -> dict[str, Any]:
    store = DocStore()

    claims = _latest_by(store.all("claims"), "claim_id")

    scored = [
        claim for claim in claims.values() if claim.verdict is not None
    ]

    overrides = _latest_by(
        store.all("verdict_overrides"),
        "claim_id",
    )

    overridden = sum(
        1
        for claim_id in overrides
        if claim_id in claims and claims[claim_id].verdict is not None
    )

    total = len(scored)

    accept_rate = (
        round((total - overridden) / total, 4) if total > 0 else None
    )

    return {
        "total_verdicts": total,
        "overridden": overridden,
        "accept_rate": accept_rate,
    }
