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


def test_report_includes_structured_claims(tmp_path, monkeypatch):
    store = DocStore(tmp_path)
    monkeypatch.setattr(report_module, "DocStore", lambda: store)

    paper = Paper(
        paper_id="p-report-003",
        title="Structured Report",
        authors=["Author"],
        year=2026,
        source=SourceType.TEXT,
        path=str(tmp_path / "paper.txt"),
        ingested_at="2026-01-01T00:00:00",
        blocks=[],
    )
    store.save("papers", paper)

    claim = make_claim(claim_id="cl-rpt-002", paper_id="p-report-003")
    store.save("claims", claim)

    monkeypatch.setattr(report_module, "run_flags", lambda *a, **kw: [])

    response = client.get("/report/p-report-003")

    assert response.status_code == 200

    data = response.json()

    assert len(data["claims"]) == 1

    record = data["claims"][0]

    assert record["claim_id"] == "cl-rpt-002"
    assert record["claim_text"] == "X improves Y"
    assert record["source_sentence"] == "X improved Y."
    assert record["start_offset"] == 0
    assert record["end_offset"] == 13
    assert record["flags"] == []
    assert data["contradictions"] == []


def test_report_includes_stored_evidence(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    store = DocStore(tmp_path)
    monkeypatch.setattr(report_module, "DocStore", lambda: store)

    paper = Paper(
        paper_id="p-report-005",
        title="Evidence Paper",
        authors=["A"],
        year=2024,
        source=SourceType.PDF,
        path="/tmp/x.pdf",
        ingested_at=datetime.now(timezone.utc),
    )
    store.save("papers", paper)

    claim = make_claim(claim_id="cl-rpt-003", paper_id="p-report-005")
    claim.supporting_evidence = [
        {"paper_id": "p-report-005", "text": "Entailing sentence.", "score": 0.71}
    ]
    claim.contradicting_evidence = [
        {"paper_id": "p-report-005", "text": "Countering sentence.", "score": 0.8}
    ]
    store.save("claims", claim)

    monkeypatch.setattr(report_module, "run_flags", lambda *a, **kw: [])

    response = client.get("/report/p-report-005")

    assert response.status_code == 200

    record = response.json()["claims"][0]

    assert len(record["supporting_evidence"]) == 1
    assert record["supporting_evidence"][0]["text"] == (
        "Entailing sentence."
    )
    assert len(record["contradicting_evidence"]) == 1


def test_report_persists_flags(tmp_path, monkeypatch):
    store = DocStore(tmp_path)
    monkeypatch.setattr(report_module, "DocStore", lambda: store)

    paper = Paper(
        paper_id="p-report-006",
        title="Flag Paper",
        authors=["A"],
        year=2024,
        source=SourceType.TEXT,
        path="/tmp/x.txt",
        ingested_at="2026-01-01T00:00:00",
        blocks=[],
    )
    store.save("papers", paper)

    claim = make_claim(claim_id="cl-rpt-flags", paper_id="p-report-006")
    claim.sample_size = 12
    store.save("claims", claim)

    response = client.get("/report/p-report-006")

    assert response.status_code == 200

    record = response.json()["claims"][0]

    assert len(record["flags"]) == 1
    assert record["flags"][0]["flag_type"] == "small_sample"

    stored = store.all("flags")

    assert len(stored) == 1
    assert stored[0].claim_id == "cl-rpt-flags"
    assert record["flags"][0]["flag_id"] == stored[0].flag_id


def test_report_includes_contradictions(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    from app.schemas import ClaimPairVerdict, Relation

    store = DocStore(tmp_path)
    monkeypatch.setattr(report_module, "DocStore", lambda: store)

    paper = Paper(
        paper_id="p-report-004",
        title="Contradiction Report",
        authors=["Author"],
        year=2026,
        source=SourceType.TEXT,
        path=str(tmp_path / "paper.txt"),
        ingested_at="2026-01-01T00:00:00",
        blocks=[],
    )
    store.save("papers", paper)

    claim_a = make_claim(claim_id="cl-rpt-a", paper_id="p-report-004")
    claim_b = make_claim(claim_id="cl-rpt-b", paper_id="p-report-004")
    store.save("claims", claim_a)
    store.save("claims", claim_b)

    verdict = ClaimPairVerdict(
        pair_id="cp-rpt-001",
        claim_id_a="cl-rpt-a",
        claim_id_b="cl-rpt-b",
        relation=Relation.CONTRADICTION,
        confidence_score=0.91,
        nli_probability=0.91,
        nli_model="test-nli",
        threshold=0.7,
        checked_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    store.save("pair_verdicts", verdict)

    support_verdict = verdict.model_copy()
    support_verdict.pair_id = "cp-rpt-002"
    support_verdict.relation = Relation.SUPPORT
    store.save("pair_verdicts", support_verdict)

    monkeypatch.setattr(report_module, "run_flags", lambda *a, **kw: [])

    response = client.get("/report/p-report-004")

    assert response.status_code == 200

    data = response.json()

    assert len(data["contradictions"]) == 1

    item = data["contradictions"][0]

    assert item["pair_id"] == "cp-rpt-001"
    assert item["nli_probability"] == 0.91
    assert item["threshold"] == 0.7
    assert item["claim_a"]["claim_text"] == "X improves Y"
    assert item["claim_b"]["source_sentence"] == "X improved Y."
