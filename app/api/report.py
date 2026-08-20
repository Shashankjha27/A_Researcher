from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.flags.runner import run_flags
from app.scoring.report_builder import build_report
from app.store.doc_store import DocStore

router = APIRouter(tags=["report"])


@router.get("/report/{paper_id}")
def report(paper_id: str) -> dict[str, Any]:
    store = DocStore()

    paper = store.get("papers", paper_id)

    if paper is None:
        raise HTTPException(
            status_code=404,
            detail=f"Paper not found: {paper_id}",
        )

    claims = store.query("claims", paper_id=paper_id)

    if not claims:
        markdown = build_report([], title=paper.title)
        return {
            "paper_id": paper_id,
            "report": markdown,
        }

    claim_records: list[dict[str, Any]] = []

    for claim in claims:
        record = {
            "claim_id": claim.claim_id,
            "paper_id": claim.paper_id,
            "claim_text": claim.claim_text,
            "effect_direction": claim.effect_direction.value,
            "method_type": claim.method_type.value,
            "sample_size": claim.sample_size,
            "source_sentence": claim.provenance.source_sentence,
            "start_offset": claim.provenance.start_offset,
            "end_offset": claim.provenance.end_offset,
            "confidence_score": claim.confidence_score,
            "confidence_components": claim.confidence_components,
            "supporting_evidence": [],
            "contradicting_evidence": [],
        }

        flags = run_flags(
            record,
            known_references=set(),
            retracted_references=set(),
            paper_funding_source=paper.funding_source,
        )

        record["flags"] = flags
        claim_records.append(record)

    markdown = build_report(claim_records, title=paper.title)

    return {
        "paper_id": paper_id,
        "report": markdown,
    }
