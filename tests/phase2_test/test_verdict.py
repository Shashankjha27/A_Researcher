from unittest.mock import patch

from app.nli.verdict import build_pair_verdict
from app.schemas import Relation


def test_contradiction_maps_to_relation():
    with patch(
        "app.nli.verdict.check_relation",
        return_value=("contradiction", 0.91),
    ):
        verdict = build_pair_verdict(
            claim_id_a="claim_001",
            claim_id_b="claim_002",
            text_a="Treatment improves recovery.",
            text_b="Treatment reduces recovery.",
        )

    assert verdict.relation == Relation.CONTRADICTION
    assert verdict.nli_probability == 0.91
    assert verdict.threshold == 0.85


def test_entailment_maps_to_support():
    with patch(
        "app.nli.verdict.check_relation",
        return_value=("support", 0.88),
    ):
        verdict = build_pair_verdict(
            claim_id_a="claim_001",
            claim_id_b="claim_002",
            text_a="Treatment improves recovery.",
            text_b="Patients recover faster with the treatment.",
        )

    assert verdict.relation == Relation.SUPPORT
    assert verdict.nli_probability == 0.88


def test_no_signal_maps_to_neutral():
    with patch(
        "app.nli.verdict.check_relation",
        return_value=("neutral", 0.55),
    ):
        verdict = build_pair_verdict(
            claim_id_a="claim_001",
            claim_id_b="claim_002",
            text_a="Treatment improves recovery.",
            text_b="The study enrolled 40 adults in Norway.",
        )

    assert verdict.relation == Relation.NEUTRAL
    assert verdict.nli_probability == 0.55


def test_verdict_records_configured_threshold():
    with patch(
        "app.nli.verdict.check_relation",
        return_value=("contradiction", 0.91),
    ):
        verdict = build_pair_verdict(
            claim_id_a="claim_001",
            claim_id_b="claim_002",
            text_a="Treatment improves recovery.",
            text_b="Treatment reduces recovery.",
        )

    assert verdict.threshold == 0.85
