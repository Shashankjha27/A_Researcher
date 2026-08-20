from __future__ import annotations

DEFAULT_FUNDING_KEYWORDS = [
    "pharma",
    "pharmaceutical",
    "industry",
    "sponsored",
    "corporate",
    "commercial",
]


def check_funding_conflict(
    funding_source: str | None,
    effect_direction: str | None = None,
    keywords: list[str] | None = None,
) -> dict[str, object] | None:
    if not funding_source or not funding_source.strip():
        return None

    funding_source = funding_source.strip()
    keywords = keywords or DEFAULT_FUNDING_KEYWORDS

    matched = [
        kw for kw in keywords
        if kw.lower() in funding_source.lower()
    ]

    if matched:
        severity = "medium"
        rationale = (
            f"Funding source '{funding_source}' contains industry-related "
            f"keywords ({', '.join(matched)}). Effect direction is "
            f"'{effect_direction or 'unknown'}'."
        )
    else:
        severity = "low"
        rationale = (
            f"Funding source disclosed: '{funding_source}'. "
            f"No industry-related keywords detected."
        )

    return {
        "flag_type": "funding_conflict",
        "severity": severity,
        "rationale_string": rationale,
    }
