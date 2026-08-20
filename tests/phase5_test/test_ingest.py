from io import BytesIO

from fastapi.testclient import TestClient

from app.api import ingest as ingest_module
from app.api.main import app

client = TestClient(app)


def test_ingest_route_exists():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/ingest" in response.json()["paths"]


def test_ingest_requires_file():
    response = client.post(
        "/ingest",
        data={
            "paper_id": "p-test",
            "title": "Test",
            "year": 2026,
        },
    )

    assert response.status_code == 422


def test_ingest_rejects_bad_file(monkeypatch):
    def failing_ingest(*args, **kwargs):
        raise ValueError("no extractable text")

    monkeypatch.setattr(ingest_module, "ingest_paper", failing_ingest)

    response = client.post(
        "/ingest",
        data={
            "paper_id": "p-test",
            "title": "Test",
            "year": 2026,
        },
        files={"file": ("test.txt", BytesIO(b""), "text/plain")},
    )

    assert response.status_code == 400
    assert "no extractable text" in response.json()["detail"]


def test_ingest_saves_paper(monkeypatch, tmp_path):
    from app.schemas import Block, Paper, SourceType

    fake_paper = Paper(
        paper_id="p-ingest-001",
        title="Ingested Paper",
        authors=["Author One"],
        year=2025,
        source=SourceType.TEXT,
        path=str(tmp_path / "test.txt"),
        ingested_at="2026-01-01T00:00:00",
        blocks=[Block(section="abstract", text="Hello world.", start_offset=0, end_offset=12)],
    )

    def fake_ingest(path, paper_id, *, title, authors, year, **kwargs):
        return fake_paper

    monkeypatch.setattr(ingest_module, "ingest_paper", fake_ingest)

    response = client.post(
        "/ingest",
        data={
            "paper_id": "p-ingest-001",
            "title": "Ingested Paper",
            "authors": "Author One",
            "year": "2025",
        },
        files={"file": ("test.txt", BytesIO(b"Hello world."), "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["paper_id"] == "p-ingest-001"
