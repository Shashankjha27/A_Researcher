from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.pipeline.run import run_pipeline

router = APIRouter(tags=["verification"])


class VerifyPaper(BaseModel):
    paper_path: str
    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int = Field(ge=1900, le=2100)

    @field_validator("paper_path", "paper_id", "title")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("field must not be empty")

        return value


class VerifyRequest(BaseModel):
    papers: list[VerifyPaper] = Field(min_length=1)
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    evidence_top_k: int = Field(default=5, ge=1, le=50)
    pair_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    nli_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


@router.post("/verify")
def verify(request: VerifyRequest) -> dict[str, Any]:
    results = []

    for paper in request.papers:
        path = Path(paper.paper_path)

        if not path.is_file():
            raise HTTPException(
                status_code=400,
                detail=f"Paper not found: {paper.paper_path}",
            )

        try:
            result = run_pipeline(
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

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=str(exc),
            ) from exc

    return {
        "count": len(results),
        "results": results,
    }
