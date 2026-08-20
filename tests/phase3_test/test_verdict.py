from app.scoring.verdict import Verdict, determine_verdict


def test_small_n_dissent_is_provisional():
    result = determine_verdict(
        confidence=0.60,
        support_count=1,
        contradiction_count=0,
    )

    assert result == Verdict.PROVISIONALLY_SUPPORTED


def test_multiple_high_confidence_support_is_supported():
    result = determine_verdict(
        confidence=0.80,
        support_count=2,
        contradiction_count=0,
    )

    assert result == Verdict.SUPPORTED


def test_no_signal_is_insufficient():
    result = determine_verdict(
        confidence=0.0,
        support_count=0,
        contradiction_count=0,
    )

    assert result == Verdict.INSUFFICIENT


def test_support_and_contradiction_are_conflicting():
    result = determine_verdict(
        confidence=0.80,
        support_count=2,
        contradiction_count=1,
    )

    assert result == Verdict.CONFLICTING


def test_contradiction_without_support_is_contradicted():
    result = determine_verdict(
        confidence=0.80,
        support_count=0,
        contradiction_count=1,
    )

    assert result == Verdict.CONTRADICTED


def test_single_support_low_confidence_is_insufficient():
    result = determine_verdict(
        confidence=0.30,
        support_count=1,
        contradiction_count=0,
    )

    assert result == Verdict.INSUFFICIENT


def test_two_support_low_confidence_is_provisional():
    result = determine_verdict(
        confidence=0.50,
        support_count=2,
        contradiction_count=0,
    )

    assert result == Verdict.PROVISIONALLY_SUPPORTED