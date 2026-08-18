from __future__ import annotations

import torch
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model

    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)

    return _model


def exact_dedupe(claims: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for claim in claims:
        normalized = claim.strip()

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        result.append(normalized)

    return result


def _encode(claims: list[str]) -> torch.Tensor:
    model = _get_model()

    embeddings = model.encode(
        claims,
        convert_to_tensor=True,
        normalize_embeddings=True,
    )

    return embeddings


def cluster_claims(
    claims: list[str],
    threshold: float = 0.75,
) -> list[list[int]]:
    if not claims:
        return []

    if len(claims) == 1:
        return [[0]]

    embeddings = _encode(claims)

    similarity = torch.matmul(
        embeddings,
        embeddings.T,
    )

    visited: set[int] = set()
    clusters: list[list[int]] = []

    for index in range(len(claims)):
        if index in visited:
            continue

        cluster = [
            other
            for other in range(len(claims))
            if float(similarity[index, other]) >= threshold
        ]

        cluster = sorted(set(cluster))
        visited.update(cluster)
        clusters.append(cluster)

    return clusters


def build_candidate_pairs(
    claims: list[str],
    threshold: float = 0.75,
) -> list[tuple[int, int]]:
    deduped = exact_dedupe(claims)

    if len(deduped) < 2:
        return []

    dedupe_to_original: dict[int, list[int]] = {}
    for original_idx, claim in enumerate(claims):
        normalized = claim.strip()
        if not normalized:
            continue
        for deduped_idx, deduped_text in enumerate(deduped):
            if deduped_text == normalized:
                dedupe_to_original.setdefault(deduped_idx, []).append(original_idx)
                break

    clusters = cluster_claims(
        deduped,
        threshold=threshold,
    )

    pairs: list[tuple[int, int]] = []

    for cluster in clusters:
        for i, first_deduped in enumerate(cluster):
            for second_deduped in cluster[i + 1:]:
                for orig_a in dedupe_to_original[first_deduped]:
                    for orig_b in dedupe_to_original[second_deduped]:
                        pairs.append((orig_a, orig_b))

    return pairs
