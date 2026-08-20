from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from benchmark.scifact import evaluate, prepare_dataset

router = APIRouter(tags=["benchmark"])


class BenchmarkRequest(BaseModel):
    split: str = Field(
        default="dev",
        pattern="^(train|dev|test)$",
    )
    threshold: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
    )


@router.post("/benchmark/scifact")
def run_benchmark(request: BenchmarkRequest) -> dict[str, Any]:
    try:
        dataset = prepare_dataset(request.split)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    try:
        rows, precision, recall, f1 = evaluate(
            dataset,
            request.threshold,
            show_progress=False,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Benchmark failed: {exc}",
        ) from exc

    labels = [
        {
            "label": label,
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(score, 4),
        }
        for label, p, r, score in rows
    ]

    return {
        "split": request.split,
        "threshold": request.threshold,
        "claims_count": len(dataset),
        "labels": labels,
        "macro": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        },
    }
