import json

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


def test_null_effect_direction_coerced_to_mixed():
    chunk = "The treatment improved accuracy by 15%."

    def fake_llm(prompt: str) -> str:
        return """
        [
            {
                "claim_text": "The treatment improved accuracy by 15%.",
                "method_type": "other",
                "effect_direction": null,
                "sample_size": null,
                "source_sentence": "The treatment improved accuracy by 15%."
            }
        ]
        """

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_009",
        section="results",
        chunk_start_offset=0,
    )

    assert len(claims) == 1
    assert claims[0].effect_direction.value == "mixed"


def test_empty_array_surrender_is_refused_then_recovers():
    chunk = "The treatment improved accuracy by 15%."

    bad = """
    [
        {
            "claim_text": "The treatment improved accuracy.",
            "method_type": "other",
            "effect_direction": "positive",
            "sample_size": null,
            "source_sentence": "totally made up sentence"
        }
    ]
    """

    good = """
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

    calls = 0

    def fake_llm(prompt: str) -> str:
        nonlocal calls
        calls += 1

        return [bad, "[]", good][calls - 1]

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_010",
        section="results",
        chunk_start_offset=0,
    )

    assert calls == 3
    assert len(claims) == 1


def test_repeated_surrender_exhausts_retries_and_discards():
    chunk = "The treatment improved accuracy by 15%."

    bad = """
    [
        {
            "claim_text": "The treatment improved accuracy.",
            "method_type": "other",
            "effect_direction": "positive",
            "sample_size": null,
            "source_sentence": "totally made up sentence"
        }
    ]
    """

    calls = 0

    def fake_llm(prompt: str) -> str:
        nonlocal calls
        calls += 1

        return [bad, "[]", "[]"][calls - 1]

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_011",
        section="results",
        chunk_start_offset=0,
    )

    assert calls == 3
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


def test_suspicious_empty_array_retries_and_recovers():
    chunk = (
        "We found that the drug reduced symptoms significantly "
        "in 200 patients (p < 0.05)."
    )

    calls = 0

    def fake_llm(prompt: str) -> str:
        nonlocal calls
        calls += 1

        if calls == 1:
            return "[]"

        return json.dumps(
            [
                {
                    "claim_text": (
                        "The drug reduced symptoms significantly "
                        "in 200 patients."
                    ),
                    "method_type": "RCT",
                    "effect_direction": "negative",
                    "sample_size": 200,
                    "source_sentence": (
                        "We found that the drug reduced symptoms "
                        "significantly in 200 patients (p < 0.05)."
                    ),
                }
            ]
        )

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_012",
        section="results",
        chunk_start_offset=0,
    )

    assert calls == 2
    assert len(claims) == 1


def test_genuine_empty_accepted_without_retry():
    chunk = (
        "Previous work has explored this area. "
        "The next section outlines the setup."
    )

    calls = 0

    def fake_llm(prompt: str) -> str:
        nonlocal calls
        calls += 1
        return "[]"

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_013",
        section="introduction",
        chunk_start_offset=0,
    )

    assert calls == 1
    assert claims == []


def test_long_chunk_split_into_windows():
    sentences = [
        f"Finding number {index} shows a value of {index} percent "
        "across all measured groups."
        for index in range(60)
    ]
    chunk = " ".join(sentences)

    assert len(chunk) > 2000

    calls = 0

    def fake_llm(prompt: str) -> str:
        nonlocal calls
        calls += 1

        window_text = (
            prompt.split("TEXT:\n", 1)[1]
            .split("Only return []", 1)[0]
            .strip()
        )
        first_sentence = window_text.split(". ")[0] + "."

        return json.dumps(
            [
                {
                    "claim_text": first_sentence,
                    "method_type": "other",
                    "effect_direction": "positive",
                    "sample_size": None,
                    "source_sentence": first_sentence,
                }
            ]
        )

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text=chunk,
        paper_id="paper_014",
        section="results",
        chunk_start_offset=500,
    )

    assert calls >= 2
    assert len(claims) == calls

    offsets = [claim.provenance.start_offset for claim in claims]

    assert offsets == sorted(offsets)
    assert all(offset >= 500 for offset in offsets)

    for claim in claims:
        start = claim.provenance.start_offset - 500
        end = claim.provenance.end_offset - 500

        assert chunk[start:end] == claim.provenance.source_sentence


def test_references_section_skipped_without_llm_call():
    def fake_llm(prompt: str) -> str:
        raise AssertionError("LLM should not be called")

    claims = extract_claims_from_chunk(
        llm_call=fake_llm,
        chunk_text="[1] Smith et al. Some reference. [2] Doe et al.",
        paper_id="paper_015",
        section="references",
        chunk_start_offset=0,
    )

    assert claims == []