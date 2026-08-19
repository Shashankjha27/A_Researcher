from __future__ import annotations

NLI_WEIGHT = 0.50
EVIDENCE_WEIGHT = 0.30
AGREEMENT_WEIGHT = 0.20


def clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def calculate_confidence(
    nli_confidence: float,
    evidence_strength: float,
    agreement: float,
) -> tuple[float, dict[str, float]]:
    nli = clamp(nli_confidence)
    evidence = clamp(evidence_strength)
    agreement_score = clamp(agreement)

    score = (
        NLI_WEIGHT * nli
        + EVIDENCE_WEIGHT * evidence
        + AGREEMENT_WEIGHT * agreement_score
    )

    components = {
        "nli_confidence": nli,
        "evidence_strength": evidence,
        "agreement": agreement_score,
    }

    return round(clamp(score), 4), components


def confidence_from_signals(
    nli_probability: float,
    evidence_scores: list[float],
    agreement: float,
) -> tuple[float, dict[str, float]]:
    if evidence_scores:
        evidence_strength = (
            sum(clamp(score) for score in evidence_scores)
            / len(evidence_scores)
        )
    else:
        evidence_strength = 0.0

    return calculate_confidence(
        nli_confidence=nli_probability,
        evidence_strength=evidence_strength,
        agreement=agreement,
    )