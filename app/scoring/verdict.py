from __future__ import annotations

from enum import Enum


class Verdict(str, Enum):
    SUPPORTED = "supported"
    PROVISIONALLY_SUPPORTED = "provisionally_supported"
    CONTRADICTED = "contradicted"
    CONFLICTING = "conflicting"
    INSUFFICIENT = "insufficient"


def determine_verdict(
    confidence: float,
    support_count: int,
    contradiction_count: int,
) -> Verdict:
    if support_count == 0 and contradiction_count == 0:
        return Verdict.INSUFFICIENT

    if contradiction_count > 0 and support_count > 0:
        return Verdict.CONFLICTING

    if contradiction_count > 0:
        return Verdict.CONTRADICTED

    if support_count >= 2 and confidence >= 0.70:
        return Verdict.SUPPORTED

    if support_count > 0 and confidence >= 0.50:
        return Verdict.PROVISIONALLY_SUPPORTED

    return Verdict.INSUFFICIENT