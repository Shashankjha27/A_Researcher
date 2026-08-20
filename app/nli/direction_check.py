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


def _best_firing(
    labels: list[tuple[str, float]],
    target: str,
    threshold: float,
) -> float | None:
    firing = [
        probability
        for label, probability in labels
        if label == target and probability >= threshold
    ]

    if not firing:
        return None

    return max(firing)


def check_relation(
    text_a: str,
    text_b: str,
    threshold: float = NLI_THRESHOLD,
) -> tuple[str, float]:
    """
    Classify the pair as contradiction / support / neutral.

    Both directions are checked; contradiction takes precedence
    over entailment (same precedence as the benchmark).
    """
    label_ab, prob_ab = classify(text_a, text_b)
    label_ba, prob_ba = classify(text_b, text_a)

    labels = [
        (label_ab, prob_ab),
        (label_ba, prob_ba),
    ]

    contradiction = _best_firing(labels, "contradiction", threshold)

    if contradiction is not None:
        return "contradiction", contradiction

    support = _best_firing(labels, "entailment", threshold)

    if support is not None:
        return "support", support

    return "neutral", max(prob_ab, prob_ba)
