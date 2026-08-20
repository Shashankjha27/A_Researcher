from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.pipeline.run import run_pipeline
from app.ui.routes import set_latest_results

router = APIRouter(tags=["verification"])


class VerifyPaper(BaseModel):
    paper_path: str
    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int = Field(ge=1900)


class VerifyRequest(BaseModel):
    papers: list[VerifyPaper] = Field(min_length=1)
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    evidence_top_k: int = Field(default=5, ge=1)
    pair_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    nli_threshold: float | None = None


def _run_verification(
    path: Path,
    *,
    paper_id: str,
    title: str,
    authors: list[str],
    year: int,
    provider: str | None,
    model: str | None,
    api_key: str | None,
    evidence_top_k: int,
    pair_threshold: float,
    nli_threshold: float | None,
) -> dict[str, Any]:
    try:
        return run_pipeline(
            path,
            paper_id=paper_id,
            title=title,
            authors=authors,
            year=year,
            provider=provider,
            model=model,
            api_key=api_key,
            evidence_top_k=evidence_top_k,
            pair_threshold=pair_threshold,
            nli_threshold=nli_threshold,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post("/verify")
def verify(request: VerifyRequest) -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    for paper in request.papers:
        path = Path(paper.paper_path)

        if not path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Paper not found: {paper.paper_path}",
            )

        result = _run_verification(
            path,
            paper_id=paper.paper_id,
            title=paper.title,
            authors=paper.authors,
            year=paper.year,
            provider=request.provider,
            model=request.model,
            api_key=request.api_key,
            evidence_top_k=request.evidence_top_k,
            pair_threshold=request.pair_threshold,
            nli_threshold=request.nli_threshold,
        )

        results.append(result)

    set_latest_results(results)

    return {
        "count": len(results),
        "results": results,
    }