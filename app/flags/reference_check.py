def check_reference(
    reference_id: str | None,
    known_references: set[str],
    retracted_references: set[str] | None = None,
) -> dict[str, object] | None:
    retracted_references = retracted_references or set()

    if not reference_id or not reference_id.strip():
        return {
            "flag_type": "reference_check",
            "severity": "high",
            "rationale_string": "Reference identifier is missing.",
        }

    reference_id = reference_id.strip()

    if reference_id in retracted_references:
        return {
            "flag_type": "retracted",
            "severity": "high",
            "rationale_string": (
                f"Reference '{reference_id}' is marked as retracted."
            ),
        }

    if reference_id not in known_references:
        return {
            "flag_type": "reference_check",
            "severity": "high",
            "rationale_string": (
                f"Reference '{reference_id}' could not be verified."
            ),
        }

    return None