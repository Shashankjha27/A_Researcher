from __future__ import annotations

CONSENSUS_PHRASES = [
    "has been shown",
    "is established",
    "is well known",
    "has been demonstrated",
    "is proven",
    "is widely accepted",
    "is known to",
    "consensus",
    "established fact",
    "well established",
    "widely recognized",
    "it is clear that",
    "there is no doubt",
]


def check_single_study(
    claim_text: str | None,
    support_count: int = 0,
) -> dict[str, object] | None:
    if not claim_text:
        return None

    text_lower = claim_text.lower()

    matched = [
        phrase for phrase in CONSENSUS_PHRASES
        if phrase in text_lower
    ]

    if not matched:
        return None

    if support_count > 1:
        return None

    return {
        "flag_type": "single_study_as_consensus",
        "severity": "medium",
        "rationale_string": (
            f"Claim implies consensus ('{matched[0]}') but is "
            f"supported by only {support_count} study."
        ),
    }
