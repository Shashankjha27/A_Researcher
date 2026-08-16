import pytest

from app.pipeline.schema_gate import (
    SchemaGateError,
    parse_json_array,
    strip_json_fences,
    validate_llm_output,
)


def test_strip_json_fences():
    raw = """```json
[
    {
        "claim_text": "The treatment improved accuracy.",
        "method_type": "RCT",
        "effect_direction": "positive",
        "sample_size": 100,
        "source_sentence": "The treatment improved accuracy."
    }
]
```"""

    result = strip_json_fences(raw)

    assert result.startswith("[")
    assert result.endswith("]")


def test_parse_json_array():
    raw = """
    [
        {
            "claim_text": "The treatment improved accuracy.",
            "method_type": "RCT",
            "effect_direction": "positive",
            "sample_size": 100,
            "source_sentence": "The treatment improved accuracy."
        }
    ]
    """

    result = parse_json_array(raw)

    assert isinstance(result, list)
    assert len(result) == 1


def test_reject_invalid_json():
    with pytest.raises(SchemaGateError):
        parse_json_array("not valid json")


def test_reject_non_array():
    raw = """
    {
        "claim_text": "The treatment improved accuracy."
    }
    """

    with pytest.raises(SchemaGateError):
        parse_json_array(raw)


def test_validate_valid_claim():
    chunk = "The treatment improved accuracy."

    raw = """
    [
        {
            "claim_text": "The treatment improved accuracy.",
            "method_type": "RCT",
            "effect_direction": "positive",
            "sample_size": 100,
            "source_sentence": "The treatment improved accuracy."
        }
    ]
    """

    claims = validate_llm_output(
        raw_output=raw,
        paper_id="paper_001",
        section="results",
        chunk_text=chunk,
        chunk_start_offset=50,
    )

    assert len(claims) == 1

    claim = claims[0]

    assert claim.paper_id == "paper_001"
    assert claim.method_type.value == "RCT"
    assert claim.effect_direction.value == "positive"
    assert claim.sample_size == 100

    assert claim.provenance.source_sentence == (
        "The treatment improved accuracy."
    )

    assert claim.provenance.start_offset == 50
    assert claim.provenance.end_offset == 82


def test_reject_missing_field():
    chunk = "The treatment improved accuracy."

    raw = """
    [
        {
            "claim_text": "The treatment improved accuracy.",
            "method_type": "RCT",
            "effect_direction": "positive",
            "sample_size": 100
        }
    ]
    """

    with pytest.raises(SchemaGateError):
        validate_llm_output(
            raw_output=raw,
            paper_id="paper_002",
            section="results",
            chunk_text=chunk,
            chunk_start_offset=0,
        )


def test_reject_extra_field():
    chunk = "The treatment improved accuracy."

    raw = """
    [
        {
            "claim_text": "The treatment improved accuracy.",
            "method_type": "RCT",
            "effect_direction": "positive",
            "sample_size": 100,
            "source_sentence": "The treatment improved accuracy.",
            "unexpected_field": "bad"
        }
    ]
    """

    with pytest.raises(SchemaGateError):
        validate_llm_output(
            raw_output=raw,
            paper_id="paper_003",
            section="results",
            chunk_text=chunk,
            chunk_start_offset=0,
        )


def test_reject_invalid_method_type():
    chunk = "The treatment improved accuracy."

    raw = """
    [
        {
            "claim_text": "The treatment improved accuracy.",
            "method_type": "random_method",
            "effect_direction": "positive",
            "sample_size": 100,
            "source_sentence": "The treatment improved accuracy."
        }
    ]
    """

    with pytest.raises(SchemaGateError):
        validate_llm_output(
            raw_output=raw,
            paper_id="paper_004",
            section="results",
            chunk_text=chunk,
            chunk_start_offset=0,
        )


def test_reject_invalid_effect_direction():
    chunk = "The treatment improved accuracy."

    raw = """
    [
        {
            "claim_text": "The treatment improved accuracy.",
            "method_type": "RCT",
            "effect_direction": "very_positive",
            "sample_size": 100,
            "source_sentence": "The treatment improved accuracy."
        }
    ]
    """

    with pytest.raises(SchemaGateError):
        validate_llm_output(
            raw_output=raw,
            paper_id="paper_005",
            section="results",
            chunk_text=chunk,
            chunk_start_offset=0,
        )


def test_reject_fake_source_sentence():
    chunk = "The treatment improved accuracy."

    raw = """
    [
        {
            "claim_text": "The treatment improved accuracy.",
            "method_type": "RCT",
            "effect_direction": "positive",
            "sample_size": 100,
            "source_sentence": "The treatment greatly improved accuracy."
        }
    ]
    """

    with pytest.raises(SchemaGateError):
        validate_llm_output(
            raw_output=raw,
            paper_id="paper_006",
            section="results",
            chunk_text=chunk,
            chunk_start_offset=0,
        )


def test_reject_negative_sample_size():
    chunk = "The treatment improved accuracy."

    raw = """
    [
        {
            "claim_text": "The treatment improved accuracy.",
            "method_type": "RCT",
            "effect_direction": "positive",
            "sample_size": -10,
            "source_sentence": "The treatment improved accuracy."
        }
    ]
    """

    with pytest.raises(SchemaGateError):
        validate_llm_output(
            raw_output=raw,
            paper_id="paper_007",
            section="results",
            chunk_text=chunk,
            chunk_start_offset=0,
        )


def test_null_sample_size_is_valid():
    chunk = "The treatment improved accuracy."

    raw = """
    [
        {
            "claim_text": "The treatment improved accuracy.",
            "method_type": "other",
            "effect_direction": "positive",
            "sample_size": null,
            "source_sentence": "The treatment improved accuracy."
        }
    ]
    """

    claims = validate_llm_output(
        raw_output=raw,
        paper_id="paper_008",
        section="results",
        chunk_text=chunk,
        chunk_start_offset=0,
    )

    assert len(claims) == 1
    assert claims[0].sample_size is None


def test_empty_claim_array_is_valid():
    claims = validate_llm_output(
        raw_output="[]",
        paper_id="paper_009",
        section="results",
        chunk_text="No empirical claims here.",
        chunk_start_offset=0,
    )

    assert claims == []
def test_show_schema_gate_output():
    chunk = "The treatment improved accuracy by 15% in 200 patients."

    raw = """
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

    claims = validate_llm_output(
        raw_output=raw,
        paper_id="paper_demo",
        section="results",
        chunk_text=chunk,
        chunk_start_offset=0,
    )

    for claim in claims:
        print("\nCLAIM OUTPUT:")
        print(claim.model_dump_json(indent=2))

    assert len(claims) == 1