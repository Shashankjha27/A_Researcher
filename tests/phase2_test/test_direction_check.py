from unittest.mock import patch

from app.nli.direction_check import check_direction, check_relation


def test_contradiction_detected_in_forward_direction():
    with patch(
        "app.nli.direction_check.classify",
        side_effect=[
            ("contradiction", 0.91),
            ("neutral", 0.20),
        ],
    ):
        result = check_direction(
            "Treatment improves recovery.",
            "Treatment reduces recovery.",
        )

    assert result == (True, "contradiction", 0.91)


def test_contradiction_detected_in_reverse_direction():
    with patch(
        "app.nli.direction_check.classify",
        side_effect=[
            ("neutral", 0.20),
            ("contradiction", 0.88),
        ],
    ):
        result = check_direction(
            "Treatment improves recovery.",
            "Treatment reduces recovery.",
        )

    assert result == (True, "contradiction", 0.88)


def test_below_threshold_is_not_contradiction():
    with patch(
        "app.nli.direction_check.classify",
        side_effect=[
            ("contradiction", 0.61),
            ("neutral", 0.30),
        ],
    ):
        result = check_direction(
            "Treatment improves recovery.",
            "Treatment reduces recovery.",
            threshold=0.7,
        )

    assert result == (False, "contradiction", 0.61)


def test_relation_contradiction_takes_precedence_over_entailment():
    with patch(
        "app.nli.direction_check.classify",
        side_effect=[
            ("entailment", 0.85),
            ("contradiction", 0.80),
        ],
    ):
        result = check_relation(
            "Treatment improves recovery.",
            "Treatment reduces recovery.",
            threshold=0.7,
        )

    assert result == ("contradiction", 0.80)


def test_relation_support_from_reverse_direction():
    with patch(
        "app.nli.direction_check.classify",
        side_effect=[
            ("neutral", 0.20),
            ("entailment", 0.90),
        ],
    ):
        result = check_relation(
            "The drug lowers blood pressure.",
            "Systolic pressure dropped significantly in the treated group.",
        )

    assert result == ("support", 0.90)


def test_relation_entailment_below_threshold_is_neutral():
    with patch(
        "app.nli.direction_check.classify",
        side_effect=[
            ("entailment", 0.61),
            ("neutral", 0.30),
        ],
    ):
        result = check_relation(
            "The drug lowers blood pressure.",
            "Blood pressure changed in the study.",
            threshold=0.7,
        )

    assert result == ("neutral", 0.61)


def test_relation_neutral_returns_higher_probability():
    with patch(
        "app.nli.direction_check.classify",
        side_effect=[
            ("neutral", 0.55),
            ("neutral", 0.72),
        ],
    ):
        result = check_relation(
            "Treatment improves recovery.",
            "The study enrolled 40 adults.",
        )

    assert result == ("neutral", 0.72)