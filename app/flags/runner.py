from __future__ import annotations

from typing import Any

from app.flags.citation_laundering import check_citation_laundering
from app.flags.funding_conflict import check_funding_conflict
from app.flags.reference_check import check_reference
from app.flags.single_study import check_single_study
from app.flags.small_sample import check_small_sample


def run_flags(
    claim: dict[str, Any],
    known_references: set[str] | None = None,
    retracted_references: set[str] | None = None,
    paper_funding_source: str | None = None,
) -> list[dict[str, object]]:
    known_references = known_references or set()
    retracted_references = retracted_references or set()

    flags: list[dict[str, object]] = []

    small_sample_flag = check_small_sample(
        claim.get("sample_size")
    )

    if small_sample_flag:
        flags.append(small_sample_flag)

    citation_laundering_flag = check_citation_laundering(
        claim.get("citation_chains", [])
    )

    if citation_laundering_flag:
        flags.append(citation_laundering_flag)

    reference_flag = check_reference(
        claim.get("reference_id"),
        known_references,
        retracted_references,
    )

    if reference_flag:
        flags.append(reference_flag)

    funding_flag = check_funding_conflict(
        paper_funding_source,
        claim.get("effect_direction"),
    )

    if funding_flag:
        flags.append(funding_flag)

    support_count = len(claim.get("supporting_evidence", []))

    single_study_flag = check_single_study(
        claim.get("claim_text"),
        support_count=support_count,
    )

    if single_study_flag:
        flags.append(single_study_flag)

    # TODO: retraction flag — cross-reference paper DOI against Retraction
    # Watch database export (bundled locally). A retracted paper that
    # contradicts another claim surfaces with higher priority.

    # TODO: statistical_rigor flag — for comparative claims, flag when
    # reported Δ is within ~2σ of zero (confidence interval includes null).
    # Treat effect as unsupported if flag fires.

    return flags


