from fastapi.testclient import TestClient

from app.api import papers
from app.api.main import app

client = TestClient(app)


class _FakeStore:
    def __init__(self, docs: list, claims: list | None = None) -> None:
        self._docs = docs
        self._claims = claims or []

    def all(self, entity: str) -> list:
        return list(self._docs) if entity == "papers" else []

    def get(self, entity: str, doc_id: str):
        if entity != "papers":
            return None

        for doc in self._docs:
            if doc.paper_id == doc_id:
                return doc

        return None

    def query(self, entity: str, **filters):
        return [
            doc
            for doc in self._claims
            if getattr(doc, "paper_id", None) == filters.get("paper_id")
        ]


def test_list_papers_dedupes_and_counts(monkeypatch, paper, claim):
    duplicate = paper.model_copy()
    duplicate.title = "Updated title"

    monkeypatch.setattr(
        papers,
        "DocStore",
        lambda: _FakeStore([paper, duplicate], claims=[claim]),
    )

    response = client.get("/papers")

    assert response.status_code == 200

    items = response.json()

    assert len(items) == 1

    item = items[0]

    assert item["paper_id"] == paper.paper_id
    assert item["title"] == "Updated title"
    assert item["path"] == paper.path
    assert item["claim_count"] == 1
    assert item["retraction_status"] == "unknown"


def test_list_papers_empty_store(monkeypatch):
    monkeypatch.setattr(papers, "DocStore", lambda: _FakeStore([]))

    response = client.get("/papers")

    assert response.status_code == 200
    assert response.json() == []


def test_paper_blocks_returns_offsets(monkeypatch, paper):
    from app.schemas import Block

    paper.blocks = [
        Block(
            section="abstract",
            text="X improved Y. More text here.",
            start_offset=0,
            end_offset=29,
        ),
        Block(
            section="results",
            text="The effect was significant.",
            start_offset=30,
            end_offset=57,
        ),
    ]

    monkeypatch.setattr(
        papers,
        "DocStore",
        lambda: _FakeStore([paper]),
    )

    response = client.get(f"/papers/{paper.paper_id}/blocks")

    assert response.status_code == 200

    body = response.json()

    assert body["paper_id"] == paper.paper_id
    assert body["title"] == paper.title
    assert len(body["blocks"]) == 2
    assert body["blocks"][0]["section"] == "abstract"
    assert body["blocks"][0]["start_offset"] == 0
    assert body["blocks"][1]["end_offset"] == 57


def test_paper_blocks_unknown_paper(monkeypatch):
    monkeypatch.setattr(papers, "DocStore", lambda: _FakeStore([]))

    response = client.get("/papers/missing/blocks")

    assert response.status_code == 404
