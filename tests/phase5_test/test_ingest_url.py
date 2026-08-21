from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.api import ingest as ingest_module
from app.api.main import app
from app.schemas import Block, Paper, SourceType

client = TestClient(app)

FAKE_META = {
    "title": "ArXiv Paper",
    "authors": ["Jane Doe"],
    "year": 2023,
    "doi": None,
    "journal": None,
}


def _fake_paper(paper_id: str, path: str) -> Paper:
    return Paper(
        paper_id=paper_id,
        title="ArXiv Paper",
        authors=["Jane Doe"],
        year=2023,
        source=SourceType.PDF,
        path=path,
        ingested_at="2026-01-01T00:00:00",
        blocks=[
            Block(section="abstract", text="Hello.", start_offset=0, end_offset=6)
        ],
    )


def test_ingest_url_happy_path(monkeypatch):
    captured: dict = {}

    monkeypatch.setattr(
        ingest_module,
        "parse_arxiv_id",
        lambda source: "2310.12345",
    )
    monkeypatch.setattr(
        ingest_module,
        "fetch_arxiv_metadata",
        lambda arxiv_id: dict(FAKE_META),
    )

    def fake_download(arxiv_id: str, dest: Path) -> Path:
        dest.write_bytes(b"%PDF-fake")
        return dest

    def fake_ingest(path, paper_id, **kwargs):
        captured["paper_id"] = paper_id
        captured.update(kwargs)

        return _fake_paper(paper_id, str(path))

    monkeypatch.setattr(
        ingest_module,
        "download_arxiv_pdf",
        fake_download,
    )
    monkeypatch.setattr(
        ingest_module,
        "ingest_paper",
        fake_ingest,
    )
    monkeypatch.setattr(
        ingest_module.DocStore,
        "save",
        lambda self, name, paper: None,
    )

    response = client.post(
        "/ingest/url",
        json={"url": "https://arxiv.org/abs/2310.12345"},
    )

    assert response.status_code == 200
    assert response.json()["paper_id"].startswith("paper-")
    assert captured["title"] == "ArXiv Paper"
    assert captured["authors"] == ["Jane Doe"]
    assert captured["year"] == 2023


def test_ingest_url_rejects_non_arxiv():
    response = client.post(
        "/ingest/url",
        json={"url": "https://example.com/paper"},
    )

    assert response.status_code == 400
    assert "arXiv" in response.json()["detail"]


def test_ingest_url_reports_lookup_failure(monkeypatch):
    monkeypatch.setattr(
        ingest_module,
        "parse_arxiv_id",
        lambda source: "2310.12345",
    )

    def failing_fetch(arxiv_id):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(
        ingest_module,
        "fetch_arxiv_metadata",
        failing_fetch,
    )

    response = client.post(
        "/ingest/url",
        json={"url": "2310.12345"},
    )

    assert response.status_code == 502
    assert "arXiv lookup failed" in response.json()["detail"]


def test_ingest_url_reports_bad_pdf(monkeypatch):
    monkeypatch.setattr(
        ingest_module,
        "parse_arxiv_id",
        lambda source: "2310.12345",
    )
    monkeypatch.setattr(
        ingest_module,
        "fetch_arxiv_metadata",
        lambda arxiv_id: dict(FAKE_META),
    )

    def fake_download(arxiv_id: str, dest: Path) -> Path:
        dest.write_bytes(b"not a pdf")
        return dest

    monkeypatch.setattr(
        ingest_module,
        "download_arxiv_pdf",
        fake_download,
    )

    response = client.post(
        "/ingest/url",
        json={"url": "2310.12345"},
    )

    assert response.status_code == 400


def test_ingest_url_route_registered():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/ingest/url" in response.json()["paths"]
