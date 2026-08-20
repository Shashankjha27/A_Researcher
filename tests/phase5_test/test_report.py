from fastapi.testclient import TestClient

from app.api import report as report_module
from app.api.main import app
from app.schemas import Paper, SourceType
from app.store.doc_store import DocStore
from tests.conftest import make_claim

client = TestClient(app)


def test_report_route_exists():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/report/{paper_id}" in paths
    assert "get" in paths["/report/{paper_id}"]


def test_report_not_found():
    response = client.get("/report/nonexistent")

    assert response.status_code == 404
    assert "Paper not found" in response.json()["detail"]


def test_report_empty_claims(tmp_path, monkeypatch):
    store = DocStore(tmp_path)
    monkeypatch.setattr(report_module, "DocStore", lambda: store)

    paper = Paper(
        paper_id="p-report-001",
        title="Report Paper",
        authors=["Author"],
        year=2026,
        source=SourceType.TEXT,
        path=str(tmp_path / "paper.txt"),
        ingested_at="2026-01-01T00:00:00",
        blocks=[],
    )
    store.save("papers", paper)

    response = client.get("/report/p-report-001")

    assert response.status_code == 200

    data = response.json()

    assert data["paper_id"] == "p-report-001"
    assert "# Report Paper" in data["report"]


def test_report_with_claims(tmp_path, monkeypatch):
    store = DocStore(tmp_path)
    monkeypatch.setattr(report_module, "DocStore", lambda: store)

    paper = Paper(
        paper_id="p-report-002",
        title="Report With Claims",
        authors=["Author"],
        year=2026,
        source=SourceType.TEXT,
        path=str(tmp_path / "paper.txt"),
        ingested_at="2026-01-01T00:00:00",
        blocks=[],
    )
    store.save("papers", paper)

    claim = make_claim(claim_id="cl-rpt-001", paper_id="p-report-002")
    store.save("claims", claim)

    monkeypatch.setattr(report_module, "run_flags", lambda *a, **kw: [])

    response = client.get("/report/p-report-002")

    assert response.status_code == 200

    data = response.json()

    assert data["paper_id"] == "p-report-002"
    assert "X improves Y" in data["report"]
    assert "# Report With Claims" in data["report"]
