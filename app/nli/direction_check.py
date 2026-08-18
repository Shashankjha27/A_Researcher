from __future__ import annotations

from app.nli.nli_engine import classify
from config import NLI_THRESHOLD


def check_direction(
    text_a: str,
    text_b: str,
    threshold: float = NLI_THRESHOLD,
) -> tuple[bool, str, float]:
    label_ab, prob_ab = classify(text_a, text_b)
    label_ba, prob_ba = classify(text_b, text_a)

    contradiction_ab = (
        label_ab == "contradiction"
        and prob_ab >= threshold
    )

    contradiction_ba = (
        label_ba == "contradiction"
        and prob_ba >= threshold
    )

    if contradiction_ab:
        return True, label_ab, prob_ab

    if contradiction_ba:
        return True, label_ba, prob_ba

    if prob_ab >= prob_ba:
        return False, label_ab, prob_ab

    return False, label_ba, prob_ba
