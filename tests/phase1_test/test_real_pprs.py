from pathlib import Path

import httpx
import pytest

from app.llm.client import get_llm_call
from app.pipeline.extract import extract_claims_from_chunk
from app.pipeline.ingest import ingest_paper
from app.store.doc_store import DocStore


def _ollama_running() -> bool:
    import os

    if not os.environ.get("LLM_MODEL"):
        return False

    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


@pytest.mark.skipif(not _ollama_running(), reason="Ollama not running or LLM_MODEL not set")
def test_real_paper_ingest_and_extract():
    paper_path = next(Path("data/in").glob("*.pdf"))

    paper = ingest_paper(
        path=paper_path,
        paper_id=paper_path.stem,
        title=paper_path.stem,
        authors=[],
        year=2026,
    )

    assert paper.blocks

    print("\nPAPER:")
    print(paper.title)
    print("\nBLOCKS:", len(paper.blocks))

    llm_call = get_llm_call()
    extracted_claims = []

    for block in paper.blocks:
        print(f"\nSECTION: {block.section}")
        print(f"START: {block.start_offset}")
        print(f"END: {block.end_offset}")

        claims = extract_claims_from_chunk(
            llm_call=llm_call,
            chunk_text=block.text,
            paper_id=paper.paper_id,
            section=block.section,
            chunk_start_offset=block.start_offset,
        )

        extracted_claims.extend(claims)

    print("\nEXTRACTED CLAIMS:", len(extracted_claims))

    assert extracted_claims

    for claim in extracted_claims:
        print(claim.model_dump_json(indent=2))

        assert claim.paper_id == paper.paper_id
        assert claim.claim_text.strip()
        assert claim.provenance.source_sentence.strip()
        assert claim.provenance.end_offset > claim.provenance.start_offset

        source = claim.provenance.source_sentence

        assert source

    store = DocStore()

    for claim in extracted_claims:
        store.save("claims", claim)

    saved_claims = store.all("claims")

    print("\nSAVED CLAIMS:", len(saved_claims))

    assert len(saved_claims) >= len(extracted_claims)

    for claim in saved_claims[-len(extracted_claims):]:
        print(claim.model_dump_json(indent=2))


def test_golden_chunk_with_three_claims():
    chunk = (
        "The treatment increased recovery rates by 18% in 300 patients. "
        "The treatment group had a mean recovery time of 7 days compared "
        "with 10 days in the control group. "
        "The observed improvement was statistically significant with p < 0.01."
    )

    def fake_llm(prompt: str) -> str:
        return """
        [
            {
                "claim_text": "The treatment increased recovery rates by 18% in 300 patients.",
                "method_type": "RCT",
                "effect_direction": "positive",
                "sample_size": 300,
                "source_sentence": "The treatment increased recovery rates by 18% in 300 patients."
            },
            {
                "claim_text": "The treatment group had a mean recovery time of 7 days compared with 10 days in the control group.",
                "method_type": "RCT",
                "effect_direction": "positive",
                "sample_size": 300,
                "source_sentence": "The treatment group had a mean recovery time of 7 days compared with 10 days in the control group."
            },
            {
                "claim_text": "The observed improvement was statistically significant with p < 0.01.",
                "method_type": "RCT",
                "effect_direction": "positive",
                "sample_size": 300,
                "source_sentence": "The observed improvement was statistically significant with p < 0.01."
            }
        ]
        """

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_golden",
        section="results",
        chunk_start_offset=0,
    )

    assert len(claims) == 3

    assert claims[0].claim_text == (
        "The treatment increased recovery rates by 18% in 300 patients."
    )

    assert claims[1].claim_text == (
        "The treatment group had a mean recovery time of 7 days compared "
        "with 10 days in the control group."
    )

    assert claims[2].claim_text == (
        "The observed improvement was statistically significant with p < 0.01."
    )

    for claim in claims:
        assert claim.provenance.source_sentence
        assert claim.provenance.start_offset >= 0
        assert claim.provenance.end_offset > claim.provenance.start_offset

        assert (
            chunk[
                claim.provenance.start_offset:
                claim.provenance.end_offset
            ]
            == claim.provenance.source_sentence
        )