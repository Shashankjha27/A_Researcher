"""Guard for tests that need real ML models (NLI / embeddings).

Skipped when AR_SKIP_MODEL_TESTS=1 (used by CI) or when the ML stack
is not importable, so pure-logic suites stay fast and dependency-free.
"""

from __future__ import annotations

import os

import pytest


def _models_available() -> bool:
    if os.environ.get("AR_SKIP_MODEL_TESTS") == "1":
        return False

    try:
        import sentence_transformers  # noqa: F401
        import torch  # noqa: F401
    except Exception:  # noqa: BLE001 - any import failure means "not available"
        return False

    return True


requires_models = pytest.mark.skipif(
    not _models_available(),
    reason="model weights skipped (AR_SKIP_MODEL_TESTS=1 or ML stack unavailable)",
)
