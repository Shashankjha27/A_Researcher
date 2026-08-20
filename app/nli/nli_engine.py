from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import CrossEncoder

from config import NLI_MODEL


@lru_cache(maxsize=1)
def _get_model() -> CrossEncoder:
    return CrossEncoder(NLI_MODEL)


def classify(
    text_a: str,
    text_b: str,
) -> tuple[str, float]:
    if not text_a.strip() or not text_b.strip():
        raise ValueError("Both texts must be non-empty.")

    model = _get_model()

    probs = model.predict(
        [(text_a, text_b)],
        apply_softmax=True,
    )

    row = probs[0]
    index = int(np.argmax(row))
    probability = float(row[index])

    label = model.config.id2label[index].lower()

    return label, probability
