from config import SMALL_SAMPLE_N


def check_small_sample(
    sample_size: int | None,
) -> dict[str, object] | None:
    if sample_size is None:
        return None

    if sample_size < SMALL_SAMPLE_N:
        return {
            "flag_type": "small_sample",
            "severity": "medium",
            "rationale_string": (
                f"Sample size ({sample_size}) is below "
                f"the minimum threshold ({SMALL_SAMPLE_N})."
            ),
        }

    return None