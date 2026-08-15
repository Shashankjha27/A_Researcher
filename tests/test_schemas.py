import pytest
from pydantic import ValidationError

from app.schemas import Claim, EffectDirection, MethodType


def valid_claim() -> dict:
    return {
        "claim_id": "c1",
        "paper_id": "p1",
        "claim_text": "Aspirin lowers risk",
        "method_type": MethodType.RCT,
        "effect_direction": EffectDirection.POSITIVE,
        "provenance": {"source_sentence": "s", "start_offset": 0, "end_offset": 1},
    }


def test_valid_claim_validates() -> None:
    assert Claim(**valid_claim()).claim_id == "c1"


def test_bad_effect_direction_rejected() -> None:
    with pytest.raises(ValidationError):
        Claim(**{**valid_claim(), "effect_direction": "sideways"})


def test_missing_provenance_rejected() -> None:
    data = valid_claim()
    del data["provenance"]
    with pytest.raises(ValidationError):
        Claim(**data)


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        Claim(**{**valid_claim(), "smuggled": "junk"})


def test_json_roundtrip_identical(claim) -> None:
    assert Claim.model_validate_json(claim.model_dump_json()) == claim
