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


def test_ingest_extracts_metadata_when_missing(monkeypatch, tmp_path):
    from app.schemas import Block, Paper, SourceType

    captured: dict = {}

    fake_paper = Paper(
        paper_id="p-ingest-002",
        title="Extracted Title",
        authors=["Extracted Author"],
        year=2024,
        source=SourceType.TEXT,
        path=str(tmp_path / "test.txt"),
        ingested_at="2026-01-01T00:00:00",
        blocks=[Block(section="abstract", text="Hello.", start_offset=0, end_offset=6)],
    )

    def fake_extract(path):
        return {
            "title": "Extracted Title",
            "authors": ["Extracted Author"],
            "year": 2024,
        }

    def fake_ingest(path, paper_id, *, title, authors, year, **kwargs):
        captured["title"] = title
        captured["authors"] = authors
        captured["year"] = year

        return fake_paper

    monkeypatch.setattr(
        ingest_module,
        "extract_metadata",
        fake_extract,
    )
    monkeypatch.setattr(ingest_module, "ingest_paper", fake_ingest)

    response = client.post(
        "/ingest",
        data={"paper_id": "p-ingest-002"},
        files={"file": ("test.txt", BytesIO(b"Hello."), "text/plain")},
    )

    assert response.status_code == 200
    assert captured["title"] == "Extracted Title"
    assert captured["authors"] == ["Extracted Author"]
    assert captured["year"] == 2024


def test_ingest_explicit_metadata_wins(monkeypatch):
    from app.schemas import Paper, SourceType

    fake_paper = Paper(
        paper_id="p-ingest-003",
        title="Explicit Title",
        authors=["Explicit Author"],
        year=1999,
        source=SourceType.TEXT,
        path="/tmp/x.txt",
        ingested_at="2026-01-01T00:00:00",
        blocks=[],
    )

    def failing_extract(path):
        raise AssertionError("extraction should not run")

    def fake_ingest(path, paper_id, *, title, authors, year, **kwargs):
        return fake_paper

    monkeypatch.setattr(
        ingest_module,
        "extract_metadata",
        failing_extract,
    )
    monkeypatch.setattr(ingest_module, "ingest_paper", fake_ingest)

    response = client.post(
        "/ingest",
        data={
            "paper_id": "p-ingest-003",
            "title": "Explicit Title",
            "authors": "Explicit Author",
            "year": "1999",
        },
        files={"file": ("test.txt", BytesIO(b"Hi"), "text/plain")},
    )

    assert response.status_code == 200
