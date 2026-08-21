from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.store.demo_seed import DEMO_PAPER_ID, ensure_demo_data
from app.store.doc_store import DocStore


def _fixture_rows(entity: str) -> list[dict]:
    path = Path("data/demo") / f"demo_fixture_{entity}.jsonl"

    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def test_fixtures_exist_and_are_consistent() -> None:
    papers = _fixture_rows("papers")
    claims = _fixture_rows("claims")
    pair_verdicts = _fixture_rows("pair_verdicts")

    assert len(papers) == 1
    assert papers[0]["paper_id"] == DEMO_PAPER_ID

    assert len(claims) >= 3

    for claim in claims:
        assert claim["paper_id"] == DEMO_PAPER_ID

    contradictions = [
        verdict
        for verdict in pair_verdicts
        if verdict["relation"] == "contradiction"
    ]

    assert contradictions, "demo fixture must contain a contradiction"

    claim_ids = {claim["claim_id"] for claim in claims}

    for verdict in pair_verdicts:
        assert verdict["claim_id_a"] in claim_ids
        assert verdict["claim_id_b"] in claim_ids


def test_ensure_demo_data_seeds_when_missing(tmp_path) -> None:
    store = DocStore(tmp_path)

    seeded = ensure_demo_data(store)

    assert seeded is True

    paper = store.get("papers", DEMO_PAPER_ID)

    assert paper is not None

    claims = store.query("claims", paper_id=DEMO_PAPER_ID)

    assert len(claims) == len(_fixture_rows("claims"))


def test_ensure_demo_data_is_noop_when_present(tmp_path) -> None:
    store = DocStore(tmp_path)

    assert ensure_demo_data(store) is True
    assert ensure_demo_data(store) is False

    claims = store.query("claims", paper_id=DEMO_PAPER_ID)

    assert len(claims) == len(_fixture_rows("claims"))


def test_demo_info_endpoint() -> None:
    from app.api.main import app

    client = TestClient(app)

    response = client.get("/demo/info")

    assert response.status_code == 200

    body = response.json()

    assert body["paper_id"] == DEMO_PAPER_ID
