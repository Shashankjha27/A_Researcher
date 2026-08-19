from __future__ import annotations

from typing import Any

from app.flags.citation_laundering import check_citation_laundering
from app.flags.reference_check import check_reference
from app.flags.small_sample import check_small_sample


def run_flags(
    claim: dict[str, Any],
    known_references: set[str] | None = None,
    retracted_references: set[str] | None= None,
) -> list[dict[str,object]]:
    known_references =  known_references or set()
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

    return flags


