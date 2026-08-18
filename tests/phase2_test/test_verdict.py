from unittest.mock import patch

from app.nli.verdict import build_pair_verdict
from app.schemas import Relation


def test_verdict_records_configured_threshold():
    with patch(
        "app.nli.verdict.check_direction",
        return_value=(True, "contradiction", 0.91),
    ):
        verdict = build_pair_verdict(
            claim_id_a="claim_001",
            claim_id_b="claim_002",
            text_a="Treatment improves recovery.",
            text_b="Treatment reduces recovery.",
        )

    assert verdict.relation == Relation.CONTRADICTION
    assert verdict.nli_probability == 0.91
    assert verdict.threshold == 0.7