from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer, util

from config import EMBEDDING_MODEL


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)


def retrieve_evidence(
    claim: str,
    sentences: list[str],
    top_k: int = 5,
) -> list[tuple[str, float]]:
    if not claim.strip():
        raise ValueError("claim must not be empty")

    if not sentences:
        return []

    top_k = min(top_k, len(sentences))

    model = _get_model()

    claim_embedding = model.encode(claim, convert_to_tensor=True)
    sentence_embeddings = model.encode(sentences, convert_to_tensor=True)

    hits = util.semantic_search(
        claim_embedding,
        sentence_embeddings,
        top_k=top_k,
    )[0]

    return [(sentences[hit["corpus_id"]], hit["score"]) for hit in hits]
