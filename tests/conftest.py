import pytest

from app.schemas import Claim, EffectDirection, MethodType, Paper, SourceType


def make_paper(paper_id: str = "p_0001") -> Paper:
    return Paper(
        paper_id=paper_id,
        title="Test paper",
        authors=["Alice", "Bob"],
        year=2020,
        source=SourceType.TEXT,
        path="data/in/test.txt",
        ingested_at="2026-01-01T00:00:00",
    )


def make_claim(claim_id: str = "c_0001", paper_id: str = "p_0001") -> Claim:
    return Claim(
        claim_id=claim_id,
        paper_id=paper_id,
        claim_text="X improves Y",
        method_type=MethodType.RCT,
        effect_direction=EffectDirection.POSITIVE,
        provenance={"source_sentence": "X improved Y.", "start_offset": 0, "end_offset": 13},
    )


@pytest.fixture
def store(tmp_path):
    from app.store.doc_store import DocStore

    return DocStore(tmp_path)


@pytest.fixture
def paper() -> Paper:
    return make_paper()


@pytest.fixture
def claim() -> Claim:
    return make_claim()
