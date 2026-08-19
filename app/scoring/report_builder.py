from __future__ import annotations

from collections import defaultdict
from typing import Any


def _format_components(components: dict[str, float]) -> str:
    if not components:
        return "No confidence components available."

    lines = [
        "| Component | Score |",
        "|---|---:|",
    ]

    for name, score in components.items():
        lines.append(f"| {name.replace('_', ' ').title()} | {score:.4f} |")

    return "\n".join(lines)


def _format_evidence(
    evidence: list[dict[str, Any]],
    heading: str,
) -> str:
    lines = [f"**{heading}**"]

    if not evidence:
        lines.append("- None")
        return "\n".join(lines)

    for item in evidence:
        paper = item.get("paper_id", "Unknown paper")
        text = item.get("text", "")
        score = item.get("score")

        if score is None:
            lines.append(f"- **{paper}:** {text}")
        else:
            lines.append(f"- **{paper}:** {text} `(score: {score:.4f})`")

    return "\n".join(lines)


def build_report(
    claims: list[dict[str, Any]],
    title: str = "Research Report",
) -> str:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for claim in claims:
        topic = claim.get("sub_topic") or claim.get("effect_direction") or "General"
        groups[str(topic)].append(claim)

    lines = [f"# {title}", ""]

    for topic, topic_claims in groups.items():
        lines.extend(
            [
                f"## {topic}",
                "",
            ]
        )

        for index, claim in enumerate(topic_claims, start=1):
            claim_text = claim.get("claim_text", "")
            confidence = float(claim.get("confidence_score", 0.0))
            verdict = claim.get("verdict", "insufficient")
            components = claim.get("confidence_components", {})

            lines.extend(
                [
                    f"### Claim {index}",
                    "",
                    claim_text,
                    "",
                    f"**Verdict:** {str(verdict).upper()}",
                    f"**Confidence:** {confidence:.4f}",
                    "",
                    _format_components(components),
                    "",
                ]
            )

            lines.append(
                _format_evidence(
                    claim.get("supporting_evidence", []),
                    "Supporting evidence",
                )
            )
            lines.append("")

            lines.append(
                _format_evidence(
                    claim.get("contradicting_evidence", []),
                    "Contradicting evidence",
                )
            )
            lines.append("")

            flags = claim.get("flags", [])

            lines.append("**Flags**")

            if flags:
                for flag in flags:
                    if isinstance(flag, dict):
                        flag_type = flag.get("flag_type", "unknown")
                        severity = flag.get("severity", "unknown")
                        rationale = flag.get("rationale_string", "")
                        lines.append(
                            f"- {flag_type} ({severity}): {rationale}"
                        )
                    else:
                        lines.append(f"- {flag}")
            else:
                lines.append("- None")

            lines.append("")

    return "\n".join(lines).rstrip() + "\n"