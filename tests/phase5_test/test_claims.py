from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import claims as claims_module
from app.api.main import app
from app.schemas import ClaimPairVerdict, Relation
from app.store.doc_store import DocStore
from tests.conftest import make_claim

client = TestClient(app)


def test_claims_route_exists():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/claims/{claim_id}" in response.json()["paths"]


def test_claims_not_found():
    response = client.get("/claims/nonexistent")

    assert response.status_code == 404
    assert "Claim not found" in response.json()["detail"]


def test_claims_returns_claim_and_verdicts(tmp_path, monkeypatch):
    store = DocStore(tmp_path)
    monkeypatch.setattr(claims_module, "DocStore", lambda: store)

    claim = make_claim(claim_id="cl-test-001", paper_id="p-test-001")
    store.save("claims", claim)

    response = client.get("/claims/cl-test-001")

    assert response.status_code == 200

    data = response.json()

    assert data["claim"]["claim_id"] == "cl-test-001"
    assert data["claim"]["claim_text"] == "X improves Y"
    assert isinstance(data["linked_verdicts"], list)


def test_claims_includes_linked_verdicts(tmp_path, monkeypatch):
    store = DocStore(tmp_path)
    monkeypatch.setattr(claims_module, "DocStore", lambda: store)

    claim = make_claim(claim_id="cl-v-001", paper_id="p-v-001")
    store.save("claims", claim)

    verdict = ClaimPairVerdict(
        pair_id="cp-001",
        claim_id_a="cl-v-001",
        claim_id_b="cl-v-002",
        relation=Relation.CONTRADICTION,
        confidence_score=0.91,
        nli_probability=0.91,
        nli_model="test-model",
        threshold=0.70,
        checked_at=datetime.now(timezone.utc),
    )
    store.save("pair_verdicts", verdict)

    response = client.get("/claims/cl-v-001")

    assert response.status_code == 200

    data = response.json()

    assert len(data["linked_verdicts"]) == 1
    assert data["linked_verdicts"][0]["pair_id"] == "cp-001"
    assert data["linked_verdicts"][0]["relation"] == "contradiction"
