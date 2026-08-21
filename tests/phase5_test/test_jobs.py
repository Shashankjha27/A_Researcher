import time

from fastapi.testclient import TestClient

from app.api import jobs
from app.api.main import app

client = TestClient(app)


def _wait_for_job(job_id: str, timeout: float = 10.0) -> dict:
    deadline = time.time() + timeout

    while time.time() < deadline:
        response = client.get(f"/jobs/{job_id}")

        assert response.status_code == 200

        payload = response.json()

        if payload["status"] in ("done", "error"):
            return payload

        time.sleep(0.05)

    raise AssertionError(f"Job {job_id} did not finish in time")


def _verify_request(tmp_path, count: int = 1) -> dict:
    papers = []

    for index in range(count):
        path = tmp_path / f"paper-{index}.txt"
        path.write_text("Sample paper text.")

        papers.append(
            {
                "paper_path": str(path),
                "paper_id": f"paper-job-{index}",
                "title": f"Job Paper {index}",
                "authors": ["Author A"],
                "year": 2026,
            }
        )

    return {"papers": papers}


def test_submit_verify_job_completes(monkeypatch, tmp_path):
    jobs.clear_jobs()

    stages: list[str] = []

    def fake_run_pipeline(paper_path, *, progress_callback=None, **kwargs):
        if progress_callback is not None:
            for stage in ("ingest", "extract", "evidence", "nli", "score"):
                stages.append(stage)
                progress_callback(stage)

        return {
            "paper": {"paper_id": kwargs["paper_id"]},
            "claims": [],
            "pair_verdicts": [],
            "report": "report",
        }

    monkeypatch.setattr(jobs, "run_pipeline", fake_run_pipeline)

    response = client.post(
        "/verify/jobs",
        json=_verify_request(tmp_path, count=2),
    )

    assert response.status_code == 202

    job_id = response.json()["job_id"]

    payload = _wait_for_job(job_id)

    assert payload["status"] == "done"
    assert payload["error"] is None
    assert payload["progress"]["total"] == 2
    assert payload["progress"]["done"] == 2
    assert len(payload["results"]) == 2
    assert set(stages) == {"ingest", "extract", "evidence", "nli", "score"}


def test_verify_job_error_is_captured(monkeypatch, tmp_path):
    jobs.clear_jobs()

    def failing_run_pipeline(paper_path, *, progress_callback=None, **kwargs):
        raise RuntimeError("extraction exploded")

    monkeypatch.setattr(jobs, "run_pipeline", failing_run_pipeline)

    response = client.post(
        "/verify/jobs",
        json=_verify_request(tmp_path),
    )

    job_id = response.json()["job_id"]

    payload = _wait_for_job(job_id)

    assert payload["status"] == "error"
    assert "extraction exploded" in payload["error"]

    health = client.get("/health")

    assert health.status_code == 200


def test_verify_job_rejects_missing_paper(tmp_path):
    jobs.clear_jobs()

    request = _verify_request(tmp_path)
    request["papers"][0]["paper_path"] = "/does/not/exist.pdf"

    response = client.post("/verify/jobs", json=request)

    assert response.status_code == 400
    assert "Paper not found" in response.json()["detail"]


def test_verify_job_requires_papers():
    response = client.post(
        "/verify/jobs",
        json={"papers": []},
    )

    assert response.status_code == 422


def test_unknown_job_returns_404():
    response = client.get("/jobs/job_does_not_exist")

    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]


def test_list_jobs_returns_history(monkeypatch, tmp_path):
    jobs.clear_jobs()

    monkeypatch.setattr(
        jobs,
        "run_pipeline",
        lambda paper_path, *, progress_callback=None, **kwargs: {
            "paper": {"paper_id": kwargs["paper_id"]},
            "claims": [],
            "pair_verdicts": [],
            "report": "report",
        },
    )

    client.post("/verify/jobs", json=_verify_request(tmp_path))

    listing = client.get("/jobs")

    assert listing.status_code == 200

    entries = listing.json()

    assert len(entries) >= 1
    assert entries[0]["kind"] == "verify"


def test_benchmark_job_completes(monkeypatch):
    jobs.clear_jobs()

    payload_stub = {
        "split": "dev",
        "threshold": 0.7,
        "claims_count": 0,
        "labels": [],
        "macro": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
    }

    monkeypatch.setattr(
        jobs,
        "run_scifact_benchmark",
        lambda request: payload_stub,
    )

    response = client.post(
        "/benchmark/scifact/jobs",
        json={"split": "dev", "threshold": 0.7},
    )

    assert response.status_code == 202

    payload = _wait_for_job(response.json()["job_id"])

    assert payload["status"] == "done"
    assert payload["results"] == [payload_stub]


def test_job_events_stream_sends_initial_event(monkeypatch):
    import json

    monkeypatch.setattr(jobs, "SSE_MAX_IDLE_TICKS", 2)

    job = jobs._create_job("verify", total=3)

    with client.stream("GET", f"/jobs/{job.job_id}/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "text/event-stream"
        )

        events = [
            line
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]

    assert len(events) == 1

    payload = json.loads(events[0][len("data: ") :])

    assert payload["job_id"] == job.job_id
    assert payload["status"] == "queued"
    assert payload["progress"]["total"] == 3


def test_job_events_stream_closes_on_completion():
    import json

    job = jobs._create_job("benchmark", total=1)
    jobs._mark(job.job_id, status="done", results=[], stage=None)

    with client.stream("GET", f"/jobs/{job.job_id}/events") as response:
        events = [
            line
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]

    assert len(events) == 1

    payload = json.loads(events[0][len("data: ") :])

    assert payload["status"] == "done"


def test_job_events_unknown_job_404():
    response = client.get("/jobs/job_missing/events")

    assert response.status_code == 404
