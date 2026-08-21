from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, HTTPException

from app.flags.runner import run_flags
from app.schemas import Flag
from app.scoring.report_builder import build_report
from app.store.doc_store import DocStore
from config import NLI_MODEL

router = APIRouter(tags=["report"])


def _claim_side(
    store: DocStore,
    claims_by_id: dict[str, dict[str, Any]],
    claim_id: str,
) -> dict[str, Any] | None:
    record = claims_by_id.get(claim_id)

    if record is None:
        claim = store.get("claims", claim_id)

        if claim is None:
            return None

        record = {
            "claim_id": claim.claim_id,
            "paper_id": claim.paper_id,
            "claim_text": claim.claim_text,
            "source_sentence": claim.provenance.source_sentence,
        }

    return {
        "claim_id": record["claim_id"],
        "paper_id": record["paper_id"],
        "claim_text": record["claim_text"],
        "source_sentence": record.get("source_sentence"),
    }


def _build_contradictions(
    store: DocStore,
    claim_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    claims_by_id = {
        record["claim_id"]: record for record in claim_records
    }

    contradictions: list[dict[str, Any]] = []

    for verdict in store.all("pair_verdicts"):
        if verdict.relation.value != "contradiction":
            continue

        if (
            verdict.claim_id_a not in claims_by_id
            and verdict.claim_id_b not in claims_by_id
        ):
            continue

        contradictions.append(
            {
                "pair_id": verdict.pair_id,
                "nli_probability": verdict.nli_probability,
                "threshold": verdict.threshold,
                "checked_at": verdict.checked_at,
                "claim_a": _claim_side(
                    store,
                    claims_by_id,
                    verdict.claim_id_a,
                ),
                "claim_b": _claim_side(
                    store,
                    claims_by_id,
                    verdict.claim_id_b,
                ),
            }
        )

    return contradictions


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
            "claims": [],
            "contradictions": [],
        }

    claim_records: list[dict[str, Any]] = []

    overrides_by_claim: dict[str, Any] = {}

    for override in store.query("verdict_overrides", paper_id=paper_id):
        overrides_by_claim[override.claim_id] = override

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
            "support_count": claim.support_count,
            "contradiction_count": claim.contradiction_count,
            "verdict": (
                claim.verdict.value if claim.verdict is not None else None
            ),
            "supporting_evidence": claim.supporting_evidence,
            "contradicting_evidence": claim.contradicting_evidence,
        }

        flags = run_flags(
            record,
            known_references=set(),
            retracted_references=set(),
            paper_funding_source=paper.funding_source,
        )

        record["flags"] = flags

        for flag in flags:
            flag_id = f"fl_{hashlib.sha1(claim.claim_id.encode() + flag['flag_type'].encode()).hexdigest()[:12]}"

            store.save(
                "flags",
                Flag(
                    flag_id=flag_id,
                    claim_id=claim.claim_id,
                    flag_type=flag["flag_type"],
                    severity=flag.get("severity", "medium"),
                    rationale_string=flag.get("rationale_string", ""),
                ),
            )

            flag["flag_id"] = flag_id

        override = overrides_by_claim.get(claim.claim_id)

        if override is not None:
            record["override"] = {
                "overridden_verdict": override.overridden_verdict.value,
                "original_verdict": (
                    override.original_verdict.value
                    if override.original_verdict is not None
                    else None
                ),
                "note": override.note,
            }

        claim_records.append(record)

    markdown = build_report(claim_records, title=paper.title)

    return {
        "paper_id": paper_id,
        "report": markdown,
        "claims": claim_records,
        "contradictions": _build_contradictions(store, claim_records),
        "nli_model": NLI_MODEL,
    }
