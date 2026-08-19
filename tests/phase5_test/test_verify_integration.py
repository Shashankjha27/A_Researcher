from fastapi.testclient import TestClient

from app.api import verify as verify_module
from app.api.main import app


def test_verify_runs_pipeline(monkeypatch, tmp_path):
    paper_path = tmp_path / "paper.pdf"
    paper_path.write_bytes(b"fake pdf")

    def fake_run_pipeline(
        paper_path,
        *,
        paper_id,
        title,
        authors,
        year,
        provider=None,
        model=None,
        api_key=None,
        evidence_top_k=5,
        pair_threshold=0.75,
        nli_threshold=None,
        store=None,
    ):
        return {
            "paper": {
                "paper_id": paper_id,
                "title": title,
            },
            "claims": [],
            "pair_verdicts": [],
            "report": "# Test Report",
        }

    monkeypatch.setattr(
        verify_module,
        "run_pipeline",
        fake_run_pipeline,
    )

    with TestClient(app) as client:
        response = client.post(
            "/verify",
            json={
                "papers": [
                    {
                        "paper_path": str(paper_path),
                        "paper_id": "paper-001",
                        "title": "Test Paper",
                        "authors": ["Test Author"],
                        "year": 2026,
                    }
                ]
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["paper"]["paper_id"] == "paper-001"
    assert data["results"][0]["report"] == "# Test Report"


def test_verify_handles_pipeline_error(monkeypatch, tmp_path):
    paper_path = tmp_path / "paper.pdf"
    paper_path.write_bytes(b"fake pdf")

    def failing_pipeline(*args, **kwargs):
        raise RuntimeError("pipeline failed")

    monkeypatch.setattr(
        verify_module,
        "run_pipeline",
        failing_pipeline,
    )

    with TestClient(app) as client:
        response = client.post(
            "/verify",
            json={
                "papers": [
                    {
                        "paper_path": str(paper_path),
                        "paper_id": "paper-001",
                        "title": "Test Paper",
                        "authors": [],
                        "year": 2026,
                    }
                ]
            },
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "pipeline failed"
