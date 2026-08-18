from app.nli.pair_reduction import (
    build_candidate_pairs,
    exact_dedupe,
)


def test_exact_dedupe():
    claims = [
        "The treatment improved recovery.",
        "The treatment improved recovery.",
        "The treatment reduced hospital stay.",
    ]

    result = exact_dedupe(claims)

    assert result == [
        "The treatment improved recovery.",
        "The treatment reduced hospital stay.",
    ]


def test_exact_dedupe_removes_empty_claims():
    claims = [
        "",
        "   ",
        "The treatment improved recovery.",
    ]

    result = exact_dedupe(claims)

    assert result == [
        "The treatment improved recovery.",
    ]


def test_build_candidate_pairs_single_claim():
    claims = [
        "The treatment improved recovery.",
    ]

    assert build_candidate_pairs(claims) == []