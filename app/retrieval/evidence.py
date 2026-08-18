from __future__ import annotations

from functools import lru_cache

import torch
from transformers import AutoModel, AutoTokenizer

from config import CONTRIEVER_MODEL


@lru_cache(maxsize=1)
def _load_model():
    tokenizer = AutoTokenizer.from_pretrained(CONTRIEVER_MODEL)
    model = AutoModel.from_pretrained(CONTRIEVER_MODEL)
    model.eval()
    return tokenizer, model


def _encode(texts: list[str]) -> torch.Tensor:
    tokenizer, model = _load_model()

    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        return_tensors="pt",
    )

    with torch.no_grad():
        outputs = model(**inputs)

    attention_mask = inputs["attention_mask"].unsqueeze(-1)
    token_embeddings = outputs.last_hidden_state

    summed = (token_embeddings * attention_mask).sum(dim=1)
    counts = attention_mask.sum(dim=1).clamp(min=1)
    mean_pooled = summed / counts

    return torch.nn.functional.normalize(mean_pooled, p=2, dim=1)


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

    claim_embedding = _encode([claim])
    sentence_embeddings = _encode(sentences)

    scores = torch.matmul(
        sentence_embeddings,
        claim_embedding.T,
    ).squeeze(1)

    values, indices = torch.topk(scores, k=top_k)

    return [
        (sentences[int(index)], float(score))
        for score, index in zip(values, indices)
    ]