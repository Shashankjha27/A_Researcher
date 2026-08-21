from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import debate as debate_module
from app.api.main import app
from app.schemas import Claim, DebateRecord, DebateTurn, EffectDirection, MethodType
from app.scoring.verdict import Verdict

client = TestClient(app)


def _make_claim() -> Claim:
    return Claim(
        claim_id="c_deb_0001",
        paper_id="p_0001",
        claim_text="X improves Y",
        method_type=MethodType.RCT,
        effect_direction=EffectDirection.POSITIVE,
        provenance={
            "source_sentence": "X improved Y.",
            "start_offset": 0,
            "end_offset": 13,
        },
        supporting_evidence=[
            {"paper_id": "p_0001", "text": "X improved Y.", "score": 0.9}
        ],
    )


def _make_record(claim_id: str = "c_deb_0001", model_label: str = "gemini/test") -> DebateRecord:
    return DebateRecord(
        debate_id="db_test000001",
        claim_id=claim_id,
        paper_id="p_0001",
        model=model_label,
        rounds=1,
        turns=[
            DebateTurn(role="defender", text="for"),
            DebateTurn(role="attacker", text="against"),
            DebateTurn(role="judge", text="meh"),
        ],
        judge_verdict=Verdict.INSUFFICIENT,
        judge_rationale="meh",
        created_at=datetime.now(timezone.utc),
    )


class _FakeStore:
    def __init__(self) -> None:
        self.claims: dict = {}
        self.debates: list = []

    def get(self, entity: str, doc_id: str):
        if entity == "claims":
            return self.claims.get(doc_id)

        return None

    def query(self, entity: str, **filters):
        if entity == "debates":
            return [
                record
                for record in self.debates
                if record.claim_id == filters.get("claim_id")
            ]

        return []

    def save(self, entity: str, doc) -> None:
        self.debates.append(doc)


def test_post_debate_runs_and_saves(monkeypatch):
    store = _FakeStore()
    store.claims["c_deb_0001"] = _make_claim()

    monkeypatch.setattr(debate_module, "DocStore", lambda: store)

    captured: dict = {}

    def fake_run_debate(**kwargs):
        captured.update(kwargs)
        return _make_record(model_label=kwargs["model_label"])

    monkeypatch.setattr(debate_module, "run_debate", fake_run_debate)

    class _FakeConfig:
        provider = "gemini"
        model = "test-model"

    monkeypatch.setattr(
        debate_module,
        "resolve_llm_config",
        lambda *args, **kwargs: _FakeConfig(),
    )
    monkeypatch.setattr(
        debate_module,
        "get_llm_call",
        lambda **kwargs: lambda prompt: "ok",
    )

    response = client.post("/claims/c_deb_0001/debate", json={})

    assert response.status_code == 200

    body = response.json()

    assert body["judge_verdict"] == "insufficient"
    assert len(body["turns"]) == 3
    assert body["model"] == "gemini/test-model"
    assert captured["evidence_texts"] == ["X improved Y."]
    assert len(store.debates) == 1


def test_post_debate_unknown_claim(monkeypatch):
    monkeypatch.setattr(debate_module, "DocStore", lambda: _FakeStore())

    response = client.post("/claims/missing/debate", json={})

    assert response.status_code == 404


def test_post_debate_no_llm_configured(monkeypatch):
    store = _FakeStore()
    store.claims["c_deb_0001"] = _make_claim()

    monkeypatch.setattr(debate_module, "DocStore", lambda: store)

    def failing_config(*args, **kwargs):
        raise ValueError("No LLM model configured.")

    monkeypatch.setattr(debate_module, "resolve_llm_config", failing_config)

    response = client.post("/claims/c_deb_0001/debate", json={})

    assert response.status_code == 400
    assert "No LLM model configured" in response.json()["detail"]


def test_get_debate_latest(monkeypatch):
    store = _FakeStore()
    older = _make_record()
    newer = _make_record()
    newer.debate_id = "db_newer"
    newer.created_at = older.created_at.replace(year=2027)
    store.debates = [older, newer]

    monkeypatch.setattr(debate_module, "DocStore", lambda: store)

    response = client.get("/claims/c_deb_0001/debate")

    assert response.status_code == 200
    assert response.json()["debate_id"] == "db_newer"


def test_get_debate_missing(monkeypatch):
    monkeypatch.setattr(debate_module, "DocStore", lambda: _FakeStore())

    response = client.get("/claims/c_none/debate")

    assert response.status_code == 404
