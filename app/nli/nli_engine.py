from __future__ import annotations

from functools import lru_cache

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from config import NLI_MODEL


@lru_cache(maxsize=1)
def _get_model():
    tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL)
    model.eval()
    return tokenizer, model


def classify(
    text_a: str,
    text_b: str,
) -> tuple[str, float]:
    if not text_a.strip() or not text_b.strip():
        raise ValueError("Both texts must be non-empty.")

    tokenizer, model = _get_model()

    inputs = tokenizer(
        text_a,
        text_b,
        return_tensors="pt",
        truncation=True,
    )

    with torch.no_grad():
        outputs = model(**inputs)

    probabilities = torch.softmax(
        outputs.logits,
        dim=-1,
    )[0]

    index = int(torch.argmax(probabilities))
    probability = float(probabilities[index])

    label = model.config.id2label[index].lower()

    return label, probability