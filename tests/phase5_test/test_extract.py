from fastapi.testclient import TestClient

from app.api import extract as extract_module
from app.api.main import app
from app.schemas import (
    Block,
    Claim,
    EffectDirection,
    MethodType,
    Paper,
    Provenance,
    SourceType,
)
from app.store.doc_store import DocStore

client = TestClient(app)


def test_extract_route_exists():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/extract/{paper_id}" in response.json()["paths"]


def test_extract_not_found():
    response = client.post("/extract/nonexistent")

    assert response.status_code == 404
    assert "Paper not found" in response.json()["detail"]


def test_extract_no_blocks(tmp_path, monkeypatch):
    store = DocStore(tmp_path)
    monkeypatch.setattr(extract_module, "DocStore", lambda: store)

    paper = Paper(
        paper_id="p-empty-001",
        title="Empty Paper",
        authors=["Author"],
        year=2026,
        source=SourceType.TEXT,
        path=str(tmp_path / "empty.txt"),
        ingested_at="2026-01-01T00:00:00",
        blocks=[],
    )
    store.save("papers", paper)

    response = client.post("/extract/p-empty-001")

    assert response.status_code == 200
    assert response.json()["claims"] == []


def test_extract_calls_llm(monkeypatch, tmp_path):
    store = DocStore(tmp_path)
    monkeypatch.setattr(extract_module, "DocStore", lambda: store)

    paper = Paper(
        paper_id="p-ext-001",
        title="Extract Paper",
        authors=["Author"],
        year=2026,
        source=SourceType.TEXT,
        path=str(tmp_path / "paper.txt"),
        ingested_at="2026-01-01T00:00:00",
        blocks=[
            Block(
                section="results",
                text="Drug A reduced symptoms by 40%.",
                start_offset=0,
                end_offset=35,
            )
        ],
    )
    store.save("papers", paper)

    fake_claim = Claim(
        claim_id="cl-ext-001",
        paper_id="p-ext-001",
        claim_text="Drug A reduced symptoms by 40%.",
        method_type=MethodType.RCT,
        effect_direction=EffectDirection.POSITIVE,
        provenance=Provenance(
            source_sentence="Drug A reduced symptoms by 40%.",
            start_offset=0,
            end_offset=35,
        ),
    )

    def fake_extract(llm_call, chunk_text, paper_id, section, chunk_start_offset):
        return [fake_claim]

    monkeypatch.setattr(extract_module, "extract_claims_from_chunk", fake_extract)

    response = client.post("/extract/p-ext-001")

    assert response.status_code == 200

    data = response.json()

    assert data["paper_id"] == "p-ext-001"
    assert len(data["claims"]) == 1
    assert data["claims"][0]["claim_id"] == "cl-ext-001"
