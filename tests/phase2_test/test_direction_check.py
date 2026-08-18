from unittest.mock import patch

from app.nli.direction_check import check_direction


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