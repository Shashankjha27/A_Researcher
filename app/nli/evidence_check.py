from __future__ import annotations

import logging

from app.nli.direction_check import check_relation

logger = logging.getLogger(__name__)


def evidence_support_counts(
    claim_text: str,
    evidence_texts: list[str],
    threshold: float,
) -> tuple[int, int, float]:
    """
    NLI a claim against each of its retrieved evidence sentences.

    Uses the same bidirectional relation check as claim-claim
    pairs and the SciFact benchmark, so "supported" means the
    paper's own text entails the claim.

    Returns (support_count, contradiction_count, max_firing_probability)
    where the probability comes from the strongest firing pair;
    contradictions take precedence over support.
    """
    support_count = 0
    contradiction_count = 0
    max_probability = 0.0

    for evidence_text in evidence_texts:
        if not evidence_text.strip():
            continue

        relation, probability = check_relation(
            claim_text,
            evidence_text,
            threshold=threshold,
        )

        if relation == "contradiction":
            contradiction_count += 1
            max_probability = max(max_probability, probability)
        elif relation == "support":
            support_count += 1
            max_probability = max(max_probability, probability)

    logger.info(
        "evidence NLI: %d support / %d contradiction from %d sentences",
        support_count,
        contradiction_count,
        len(evidence_texts),
    )

    return support_count, contradiction_count, max_probability
