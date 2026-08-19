from app.flags.runner import run_flags


def test_runner_collects_flags():
    claim = {
        "sample_size": 10,
        "citation_chains": [
            ["paper-a", "root-a"],
            ["paper-b", "root-a"],
            ["paper-c", "root-a"],
        ],
        "reference_id": "unknown",
    }

    flags = run_flags(
        claim,
        known_references={"known"},
    )

    flag_types = {flag["flag_type"] for flag in flags}

    assert "small_sample" in flag_types
    assert "citation_laundering" in flag_types
    assert "reference_check" in flag_types


def test_runner_returns_no_flags_for_clean_claim():
    claim = {
        "sample_size": 100,
        "citation_chains": [
            ["paper-a", "root-a"],
            ["paper-b", "root-b"],
            ["paper-c", "root-c"],
        ],
        "reference_id": "known",
    }

    flags = run_flags(
        claim,
        known_references={"known"},
    )

    assert flags == []