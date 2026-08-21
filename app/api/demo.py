from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.api.jobs import _create_job, _run_verify_job
from app.api.verify import VerifyPaper, VerifyRequest
from app.store.demo_seed import DEMO_PAPER_ID

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_SOURCE = Path("data/demo/golden_contradiction.txt")

DEMO_TITLE = "Recovery Outcomes After Adjuvant Treatment (Demo)"


class DemoInfo(BaseModel):
    paper_id: str
    title: str
    source_path: str


class DemoRunLiveRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None


@router.get("/info", response_model=DemoInfo)
def demo_info() -> DemoInfo:
    return DemoInfo(
        paper_id=DEMO_PAPER_ID,
        title=DEMO_TITLE,
        source_path=str(DEMO_SOURCE),
    )


@router.post("/run-live")
def run_live_demo(
    request: DemoRunLiveRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    if not DEMO_SOURCE.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Demo source missing: {DEMO_SOURCE}",
        )

    verify_request = VerifyRequest(
        papers=[
            VerifyPaper(
                paper_path=str(DEMO_SOURCE),
                paper_id=f"{DEMO_PAPER_ID}-live",
                title=DEMO_TITLE,
                authors=["A. Author", "B. Author"],
                year=2024,
            ),
        ],
        provider=request.provider,
        model=request.model,
        api_key=request.api_key,
    )

    job = _create_job("verify", total=1)

    background_tasks.add_task(
        _run_verify_job,
        job.job_id,
        verify_request,
    )

    return {"job_id": job.job_id}
