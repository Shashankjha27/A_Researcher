from app.nli.pair_reduction import (
    build_candidate_pairs,
    cluster_claims,
    exact_dedupe,
)
from tests.model_guard import requires_models


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


@requires_models
def test_cluster_claims_no_transitive_merge():
    claims = [
        "The treatment improved recovery.",
        "The treatment improved recovery significantly.",
        "The hospital was built in 2020.",
    ]

    clusters = cluster_claims(claims, threshold=0.75)

    all_indices = [idx for cluster in clusters for idx in cluster]
    assert sorted(all_indices) == [0, 1, 2]

    dissimilar_in_same_cluster = False
    for cluster in clusters:
        if len(cluster) > 1:
            cluster_texts = [claims[i] for i in cluster]
            for i, t1 in enumerate(cluster_texts):
                for t2 in cluster_texts[i + 1 :]:
                    if "hospital" in t1 and "treatment" in t2:
                        dissimilar_in_same_cluster = True
                    if "hospital" in t2 and "treatment" in t1:
                        dissimilar_in_same_cluster = True

    assert not dissimilar_in_same_cluster
