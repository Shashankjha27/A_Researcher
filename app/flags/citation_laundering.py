from collections import Counter


def check_citation_laundering(
    citation_chains: list[list[str]],
    minimum_sources: int = 3,
) -> dict[str, object] | None:
    if len(citation_chains) < minimum_sources:
        return None

    roots = [chain[-1] for chain in citation_chains if chain]

    if not roots:
        return None

    counts = Counter(roots)

    dominant_root, dominant_count = counts.most_common(1)[0]

    if dominant_count < 2:
        return None

    return {
        "flag_type": "citation_laundering",
        "severity": "medium",
        "rationale_string": (
            f"{len(citation_chains)} supporting citation chains "
            f"trace back to {len(counts)} distinct root references; "
            f"{dominant_count} trace back to root reference "
            f"'{dominant_root}'."
        ),
    }