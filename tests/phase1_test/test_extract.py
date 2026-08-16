from app.pipeline.extract import extract_claims_from_chunk


def test_extract_valid_claim():
    chunk = (
        "The treatment improved accuracy by 15% in 200 patients. "
        "The control group showed no significant improvement."
    )

    def fake_llm(prompt: str) -> str:
        return """
        [
            {
                "claim_text": "The treatment improved accuracy by 15% in 200 patients.",
                "method_type": "RCT",
                "effect_direction": "positive",
                "sample_size": 200,
                "source_sentence": "The treatment improved accuracy by 15% in 200 patients."
            }
        ]
        """

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_001",
        section="results",
        chunk_start_offset=0,
    )

    assert len(claims) == 1

    claim = claims[0]

    assert claim.paper_id == "paper_001"
    assert claim.claim_text == (
        "The treatment improved accuracy by 15% in 200 patients."
    )
    assert claim.method_type.value == "RCT"
    assert claim.effect_direction.value == "positive"
    assert claim.sample_size == 200
    assert claim.provenance.source_sentence == (
        "The treatment improved accuracy by 15% in 200 patients."
    )
    assert claim.provenance.start_offset == 0
    assert claim.provenance.end_offset == 55


def test_extract_no_claims():
    chunk = (
        "Previous studies have investigated this problem. "
        "The following section describes the experimental setup."
    )

    def fake_llm(prompt: str) -> str:
        return "[]"

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_002",
        section="introduction",
        chunk_start_offset=100,
    )

    assert claims == []


def test_invalid_json_retries():
    chunk = "The treatment improved accuracy by 15%."

    calls = 0

    def fake_llm(prompt: str) -> str:
        nonlocal calls
        calls += 1

        if calls == 1:
            return "This is not valid JSON"

        return """
        [
            {
                "claim_text": "The treatment improved accuracy by 15%.",
                "method_type": "other",
                "effect_direction": "positive",
                "sample_size": null,
                "source_sentence": "The treatment improved accuracy by 15%."
            }
        ]
        """

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_003",
        section="results",
        chunk_start_offset=0,
    )

    assert calls == 2
    assert len(claims) == 1


def test_invalid_source_sentence_retries():
    chunk = "The treatment improved accuracy by 15%."

    calls = 0

    def fake_llm(prompt: str) -> str:
        nonlocal calls
        calls += 1

        if calls == 1:
            return """
            [
                {
                    "claim_text": "The treatment improved accuracy.",
                    "method_type": "other",
                    "effect_direction": "positive",
                    "sample_size": null,
                    "source_sentence": "The treatment significantly improved accuracy."
                }
            ]
            """

        return """
        [
            {
                "claim_text": "The treatment improved accuracy by 15%.",
                "method_type": "other",
                "effect_direction": "positive",
                "sample_size": null,
                "source_sentence": "The treatment improved accuracy by 15%."
            }
        ]
        """

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_004",
        section="results",
        chunk_start_offset=0,
    )

    assert calls == 2
    assert len(claims) == 1
    assert claims[0].provenance.source_sentence == (
        "The treatment improved accuracy by 15%."
    )


def test_invalid_method_type_is_rejected():
    chunk = "The treatment improved accuracy by 15%."

    def fake_llm(prompt: str) -> str:
        return """
        [
            {
                "claim_text": "The treatment improved accuracy by 15%.",
                "method_type": "random_method",
                "effect_direction": "positive",
                "sample_size": null,
                "source_sentence": "The treatment improved accuracy by 15%."
            }
        ]
        """

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_005",
        section="results",
        chunk_start_offset=0,
    )

    assert claims == []


def test_invalid_effect_direction_is_rejected():
    chunk = "The treatment improved accuracy by 15%."

    def fake_llm(prompt: str) -> str:
        return """
        [
            {
                "claim_text": "The treatment improved accuracy by 15%.",
                "method_type": "other",
                "effect_direction": "very_positive",
                "sample_size": null,
                "source_sentence": "The treatment improved accuracy by 15%."
            }
        ]
        """

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_006",
        section="results",
        chunk_start_offset=0,
    )

    assert claims == []


def test_empty_chunk():
    def fake_llm(prompt: str) -> str:
        raise AssertionError("LLM should not be called")

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text="   ",
        paper_id="paper_007",
        section="results",
        chunk_start_offset=0,
    )

    assert claims == []


def test_markdown_json_fences_are_handled():
    chunk = "The treatment improved accuracy by 15%."

    def fake_llm(prompt: str) -> str:
        return """```json
[
    {
        "claim_text": "The treatment improved accuracy by 15%.",
        "method_type": "other",
        "effect_direction": "positive",
        "sample_size": null,
        "source_sentence": "The treatment improved accuracy by 15%."
    }
]
```"""

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_008",
        section="results",
        chunk_start_offset=0,
    )

    assert len(claims) == 1
    assert claims[0].provenance.source_sentence == (
        "The treatment improved accuracy by 15%."
    )
    assert claims[0].provenance.start_offset == 0
    assert claims[0].provenance.end_offset == 39