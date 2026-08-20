from app.scoring.confidence import (
    AGREEMENT_WEIGHT,
    EVIDENCE_WEIGHT,
    NLI_WEIGHT,
    calculate_confidence,
    clamp,
    confidence_from_signals,
)


def test_clamp_within_range():
    assert clamp(0.5) == 0.5


def test_clamp_below_zero():
    assert clamp(-0.3) == 0.0


def test_clamp_above_one():
    assert clamp(1.5) == 1.0


def test_calculate_confidence_all_high():
    score, components = calculate_confidence(
        nli_confidence=1.0,
        evidence_strength=1.0,
        agreement=1.0,
    )

    assert score == round(NLI_WEIGHT + EVIDENCE_WEIGHT + AGREEMENT_WEIGHT, 4)
    assert components["nli_confidence"] == 1.0
    assert components["evidence_strength"] == 1.0
    assert components["agreement"] == 1.0


def test_calculate_confidence_all_zero():
    score, components = calculate_confidence(
        nli_confidence=0.0,
        evidence_strength=0.0,
        agreement=0.0,
    )

    assert score == 0.0
    assert components["nli_confidence"] == 0.0
    assert components["evidence_strength"] == 0.0
    assert components["agreement"] == 0.0


def test_calculate_confidence_weights_components():
    score, _ = calculate_confidence(
        nli_confidence=1.0,
        evidence_strength=0.0,
        agreement=0.0,
    )

    assert score == round(NLI_WEIGHT, 4)

    score, _ = calculate_confidence(
        nli_confidence=0.0,
        evidence_strength=1.0,
        agreement=0.0,
    )

    assert score == round(EVIDENCE_WEIGHT, 4)

    score, _ = calculate_confidence(
        nli_confidence=0.0,
        evidence_strength=0.0,
        agreement=1.0,
    )

    assert score == round(AGREEMENT_WEIGHT, 4)


def test_calculate_confidence_clamps_out_of_range():
    score, components = calculate_confidence(
        nli_confidence=2.0,
        evidence_strength=-1.0,
        agreement=0.5,
    )

    assert 0.0 <= score <= 1.0
    assert components["nli_confidence"] == 1.0
    assert components["evidence_strength"] == 0.0
    assert components["agreement"] == 0.5


def test_confidence_from_signals_averages_evidence():
    score, components = confidence_from_signals(
        nli_probability=0.8,
        evidence_scores=[0.8, 0.6],
        agreement=1.0,
    )

    assert components["evidence_strength"] == 0.7
    assert 0.0 <= score <= 1.0


def test_confidence_from_signals_empty_evidence():
    _, components = confidence_from_signals(
        nli_probability=0.8,
        evidence_scores=[],
        agreement=1.0,
    )

    assert components["evidence_strength"] == 0.0


def test_confidence_from_signals_clamps_negative_scores():
    score, components = confidence_from_signals(
        nli_probability=0.5,
        evidence_scores=[-0.2, 0.4],
        agreement=0.5,
    )

    assert components["evidence_strength"] == 0.2
    assert 0.0 <= score <= 1.0
