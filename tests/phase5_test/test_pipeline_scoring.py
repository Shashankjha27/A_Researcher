from datetime import datetime, timezone

from app.pipeline import run as pipeline_run
from app.schemas import Block, Claim, Paper, Provenance
from app.scoring.verdict import Verdict
from app.store.doc_store import DocStore


def _fake_claim(index: int) -> Claim:
    return Claim(
        claim_id=f"cl_p1_c{index}",
        paper_id="p1",
        claim_text=f"Claim number {index} shows improvement.",
        method_type="RCT",
        effect_direction="positive",
        provenance=Provenance(
            source_sentence=f"Claim number {index} shows improvement.",
            start_offset=index * 10,
            end_offset=index * 10 + 5,
        ),
    )


def _fake_paper() -> Paper:
    return Paper(
        paper_id="p1",
        title="Test Paper",
        authors=["A"],
        year=2024,
        source="pdf",
        path="/tmp/x.pdf",
        ingested_at=datetime.now(timezone.utc),
        blocks=[
            Block(
                section="results",
                text="Claim number 0 shows improvement.",
                start_offset=0,
                end_offset=34,
            )
        ],
    )


def test_pipeline_saves_each_claim_once_and_sets_verdict(
    monkeypatch,
    tmp_path,
):
    claims = [_fake_claim(0), _fake_claim(1)]

    monkeypatch.setattr(
        pipeline_run,
        "ingest_paper",
        lambda *args, **kwargs: _fake_paper(),
    )
    monkeypatch.setattr(
        pipeline_run,
        "get_llm_call",
        lambda **kwargs: (lambda prompt: ""),
    )
    monkeypatch.setattr(
        pipeline_run,
        "extract_claims_from_chunk",
        lambda **kwargs: list(claims),
    )
    monkeypatch.setattr(
        pipeline_run,
        "retrieve_evidence",
        lambda *args, **kwargs: [
            ("Supporting sentence one.", 0.7),
            ("Supporting sentence two.", 0.6),
        ],
    )
    monkeypatch.setattr(
        pipeline_run,
        "build_candidate_pairs",
        lambda *args, **kwargs: [],
    )

    def fake_evidence_counts(
        claim_text,
        evidence_texts,
        threshold,
    ):
        return 2, 0, 0.8

    monkeypatch.setattr(
        pipeline_run,
        "evidence_support_counts",
        fake_evidence_counts,
    )

    store = DocStore(base_dir=tmp_path / "store")

    result = pipeline_run.run_pipeline(
        "/tmp/does-not-matter.pdf",
        paper_id="p1",
        title="Test Paper",
        authors=["A"],
        year=2024,
        store=store,
    )

    stored = store.query("claims", paper_id="p1")

    assert len(stored) == 2

    for claim in stored:
        assert claim.support_count == 2
        assert claim.contradiction_count == 0
        assert claim.verdict is not None
        assert claim.confidence_score > 0
        assert len(claim.supporting_evidence) == 2
        assert claim.supporting_evidence[0]["text"] == (
            "Supporting sentence one."
        )

    report_claims = result["claims"]

    assert all(record["verdict"] for record in report_claims)
    assert all(
        record["support_count"] == 2 for record in report_claims
    )
    assert all(
        len(record["supporting_evidence"]) == 2
        for record in report_claims
    )


def test_pipeline_contradicted_verdict_from_evidence(
    monkeypatch,
    tmp_path,
):
    claims = [_fake_claim(0)]

    monkeypatch.setattr(
        pipeline_run,
        "ingest_paper",
        lambda *args, **kwargs: _fake_paper(),
    )
    monkeypatch.setattr(
        pipeline_run,
        "get_llm_call",
        lambda **kwargs: (lambda prompt: ""),
    )
    monkeypatch.setattr(
        pipeline_run,
        "extract_claims_from_chunk",
        lambda **kwargs: list(claims),
    )
    monkeypatch.setattr(
        pipeline_run,
        "retrieve_evidence",
        lambda *args, **kwargs: [("Contradicting sentence.", 0.65)],
    )
    monkeypatch.setattr(
        pipeline_run,
        "build_candidate_pairs",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        pipeline_run,
        "evidence_support_counts",
        lambda claim_text, evidence_texts, threshold: (0, 1, 0.9),
    )

    store = DocStore(base_dir=tmp_path / "store")

    result = pipeline_run.run_pipeline(
        "/tmp/does-not-matter.pdf",
        paper_id="p1",
        title="Test Paper",
        authors=["A"],
        year=2024,
        store=store,
    )

    stored = store.query("claims", paper_id="p1")

    assert len(stored) == 1
    assert stored[0].verdict == Verdict.CONTRADICTED
    assert result["claims"][0]["verdict"] == "contradicted"
