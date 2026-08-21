from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import feedback as feedback_module
from app.api.main import app
from app.schemas import (
    Claim,
    EffectDirection,
    Flag,
    FlagType,
    MethodType,
    Severity,
    VerdictOverride,
)
from app.scoring.verdict import Verdict

client = TestClient(app)


def _make_claim(claim_id: str = "c_fb_0001", verdict: str | None = "supported") -> Claim:
    return Claim(
        claim_id=claim_id,
        paper_id="p_0001",
        claim_text="X improves Y",
        method_type=MethodType.RCT,
        effect_direction=EffectDirection.POSITIVE,
        provenance={
            "source_sentence": "X improved Y.",
            "start_offset": 0,
            "end_offset": 13,
        },
        verdict=verdict,
    )


def _make_flag() -> Flag:
    return Flag(
        flag_id="f_fb_0001",
        claim_id="c_fb_0001",
        flag_type=FlagType.SMALL_SAMPLE,
        severity=Severity.LOW,
        rationale_string="n is small",
    )


class _FakeStore:
    def __init__(self) -> None:
        self.claims: dict = {}
        self.flags: dict = {}
        self.overrides: list = []
        self.reviews: list = []

    def get(self, entity: str, doc_id: str):
        source = {
            "claims": self.claims,
            "flags": self.flags,
        }.get(entity)

        if source is None:
            return None

        return source.get(doc_id)

    def all(self, entity: str) -> list:
        return {
            "claims": list(self.claims.values()),
            "verdict_overrides": list(self.overrides),
        }.get(entity, [])

    def query(self, entity: str, **filters):
        if entity == "verdict_overrides":
            return [
                record
                for record in self.overrides
                if all(
                    getattr(record, key) == value
                    for key, value in filters.items()
                )
            ]

        return []

    def save(self, entity: str, doc) -> None:
        {
            "verdict_overrides": self.overrides,
            "flag_reviews": self.reviews,
        }.get(entity, []).append(doc)


def test_override_saves_record(monkeypatch):
    store = _FakeStore()
    store.claims["c_fb_0001"] = _make_claim()

    monkeypatch.setattr(feedback_module, "DocStore", lambda: store)

    response = client.post(
        "/claims/c_fb_0001/override",
        json={"verdict": "contradicted", "note": "checked the data"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["original_verdict"] == "supported"
    assert body["overridden_verdict"] == "contradicted"
    assert body["note"] == "checked the data"
    assert len(store.overrides) == 1


def test_override_rejects_unknown_verdict(monkeypatch):
    monkeypatch.setattr(feedback_module, "DocStore", lambda: _FakeStore())

    response = client.post(
        "/claims/c_fb_0001/override",
        json={"verdict": "not-a-verdict"},
    )

    assert response.status_code == 422


def test_override_unknown_claim(monkeypatch):
    monkeypatch.setattr(feedback_module, "DocStore", lambda: _FakeStore())

    response = client.post(
        "/claims/missing/override",
        json={"verdict": "supported"},
    )

    assert response.status_code == 404


def test_get_latest_override(monkeypatch):
    store = _FakeStore()

    older = VerdictOverride(
        override_id="ov_old",
        claim_id="c_fb_0001",
        paper_id="p_0001",
        original_verdict=Verdict.SUPPORTED,
        overridden_verdict=Verdict.CONTRADICTED,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = VerdictOverride(
        override_id="ov_new",
        claim_id="c_fb_0001",
        paper_id="p_0001",
        original_verdict=Verdict.SUPPORTED,
        overridden_verdict=Verdict.INSUFFICIENT,
        created_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
    )
    store.overrides = [older, newer]

    monkeypatch.setattr(feedback_module, "DocStore", lambda: store)

    response = client.get("/claims/c_fb_0001/override")

    assert response.status_code == 200
    assert response.json()["override_id"] == "ov_new"


def test_paper_overrides_dedupes_per_claim(monkeypatch):
    store = _FakeStore()

    for claim_id in ("c_1", "c_2"):
        store.overrides.append(
            VerdictOverride(
                override_id=f"ov_{claim_id}",
                claim_id=claim_id,
                paper_id="p_0001",
                overridden_verdict=Verdict.INSUFFICIENT,
                created_at=datetime.now(timezone.utc),
            )
        )

    # duplicate (later) row for c_1
    store.overrides.append(
        VerdictOverride(
            override_id="ov_c1_later",
            claim_id="c_1",
            paper_id="p_0001",
            overridden_verdict=Verdict.SUPPORTED,
            created_at=datetime.now(timezone.utc),
        )
    )

    monkeypatch.setattr(feedback_module, "DocStore", lambda: store)

    response = client.get("/papers/p_0001/overrides")

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 2
    by_claim = {row["claim_id"]: row for row in body}
    assert by_claim["c_1"]["override_id"] == "ov_c1_later"


def test_flag_review(monkeypatch):
    store = _FakeStore()
    store.flags["f_fb_0001"] = _make_flag()

    monkeypatch.setattr(feedback_module, "DocStore", lambda: store)

    response = client.post(
        "/flags/f_fb_0001/review",
        json={"accepted": False},
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is False
    assert len(store.reviews) == 1


def test_flag_review_unknown_flag(monkeypatch):
    monkeypatch.setattr(feedback_module, "DocStore", lambda: _FakeStore())

    response = client.post(
        "/flags/missing/review",
        json={"accepted": True},
    )

    assert response.status_code == 404


def test_agreement_stats(monkeypatch):
    store = _FakeStore()
    store.claims["c_1"] = _make_claim(claim_id="c_1")
    store.claims["c_2"] = _make_claim(claim_id="c_2")
    store.claims["c_3"] = _make_claim(claim_id="c_3", verdict=None)

    store.overrides.append(
        VerdictOverride(
            override_id="ov_1",
            claim_id="c_1",
            paper_id="p_0001",
            overridden_verdict=Verdict.CONTRADICTED,
            created_at=datetime.now(timezone.utc),
        )
    )

    monkeypatch.setattr(feedback_module, "DocStore", lambda: store)

    response = client.get("/stats/agreement")

    assert response.status_code == 200

    body = response.json()

    assert body["total_verdicts"] == 2
    assert body["overridden"] == 1
    assert body["accept_rate"] == 0.5
