from __future__ import annotations

import asyncio
import json
import threading
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from app.api.benchmark import BenchmarkRequest, run_scifact_benchmark
from app.api.verify import VerifyRequest
from app.pipeline.run import run_pipeline
from app.ui.routes import set_latest_results

router = APIRouter(tags=["jobs"])

MAX_JOBS = 50

SSE_POLL_INTERVAL_S = 0.5

# close the stream after this many polls without a change; clients
# reconnect automatically (EventSource / hook retry logic)
SSE_MAX_IDLE_TICKS = 120

_jobs: dict[str, JobRecord] = {}
_lock = threading.Lock()
_job_slots = threading.Semaphore(1)


@dataclass
class JobRecord:
    job_id: str
    kind: str
    total: int
    status: str = "queued"
    done: int = 0
    stage: str | None = None
    results: list[Any] | None = None
    error: str | None = None
    created_at: str = ""


def _create_job(kind: str, total: int) -> JobRecord:
    job = JobRecord(
        job_id=f"job_{uuid.uuid4().hex[:12]}",
        kind=kind,
        total=total,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    with _lock:
        _jobs[job.job_id] = job
        _prune_locked()

    return job


def _prune_locked() -> None:
    if len(_jobs) <= MAX_JOBS:
        return

    finished = [
        job_id
        for job_id, job in _jobs.items()
        if job.status in ("done", "error")
    ]

    while len(_jobs) > MAX_JOBS and finished:
        del _jobs[finished.pop(0)]


def clear_jobs() -> None:
    with _lock:
        _jobs.clear()


def get_job(job_id: str) -> JobRecord | None:
    with _lock:
        return _jobs.get(job_id)


def _stage_callback(job_id: str):
    def callback(stage: str) -> None:
        with _lock:
            job = _jobs.get(job_id)

            if job is not None:
                job.stage = stage

    return callback


def _mark(job_id: str, **updates: Any) -> JobRecord | None:
    with _lock:
        job = _jobs.get(job_id)

        if job is None:
            return None

        for key, value in updates.items():
            setattr(job, key, value)

        return job


def _job_payload(job: JobRecord) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "kind": job.kind,
        "status": job.status,
        "progress": {
            "done": job.done,
            "total": job.total,
            "stage": job.stage,
        },
        "results": job.results,
        "error": job.error,
        "created_at": job.created_at,
    }


def _run_verify_job(job_id: str, request: VerifyRequest) -> None:
    with _job_slots:
        _mark(job_id, status="running")

        callback = _stage_callback(job_id)
        results: list[dict[str, Any]] = []

        try:
            for paper in request.papers:
                result = run_pipeline(
                    Path(paper.paper_path),
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
                    progress_callback=callback,
                )

                results.append(result)

                with _lock:
                    current = _jobs.get(job_id)

                    if current is not None:
                        current.done += 1
                        current.stage = None

            _mark(job_id, results=results, status="done", stage=None)
            set_latest_results(results)
        except Exception as exc:  # noqa: BLE001 - any failure must land in the job record
            _mark(job_id, status="error", error=str(exc), stage=None)


def _run_benchmark_job(job_id: str, request: BenchmarkRequest) -> None:
    with _job_slots:
        _mark(job_id, status="running", stage="benchmark")

        try:
            payload = run_scifact_benchmark(request)
            _mark(job_id, results=[payload], status="done", stage=None)
        except Exception as exc:  # noqa: BLE001 - any failure must land in the job record
            _mark(job_id, status="error", error=str(exc), stage=None)


@router.post("/verify/jobs", status_code=202)
def submit_verify_job(
    request: VerifyRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    for paper in request.papers:
        if not Path(paper.paper_path).exists():
            raise HTTPException(
                status_code=400,
                detail=f"Paper not found: {paper.paper_path}",
            )

    job = _create_job("verify", total=len(request.papers))

    background_tasks.add_task(_run_verify_job, job.job_id, request)

    return {"job_id": job.job_id}


@router.post("/benchmark/scifact/jobs", status_code=202)
def submit_benchmark_job(
    request: BenchmarkRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    job = _create_job("benchmark", total=1)

    background_tasks.add_task(_run_benchmark_job, job.job_id, request)

    return {"job_id": job.job_id}


@router.get("/jobs")
def list_jobs() -> list[dict[str, Any]]:
    with _lock:
        records = list(_jobs.values())

    return [_job_payload(job) for job in reversed(records)]


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}",
        )

    return _job_payload(job)


@router.get("/jobs/{job_id}/events")
async def stream_job_events(job_id: str) -> StreamingResponse:
    if get_job(job_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}",
        )

    async def event_stream() -> AsyncIterator[str]:
        last_payload: str | None = None
        idle_ticks = 0

        while True:
            job = get_job(job_id)

            if job is None:
                break

            payload = json.dumps(_job_payload(job))

            if payload != last_payload:
                last_payload = payload
                idle_ticks = 0
                yield f"data: {payload}\n\n"
            else:
                idle_ticks += 1

                if idle_ticks >= SSE_MAX_IDLE_TICKS:
                    break

            if job.status in ("done", "error"):
                break

            await asyncio.sleep(SSE_POLL_INTERVAL_S)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
