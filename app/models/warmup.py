from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def warm_models() -> dict[str, bool]:
    """Pre-load NLI / embedding models so the first real request is fast."""
    from app.models.registry import ModelRegistry

    registry = ModelRegistry()

    for name, loader in (
        ("nli", registry.nli),
        ("embeddings", registry.embeddings),
        ("contriever", registry.contriever),
    ):
        try:
            loader()
            logger.info("warm-up: %s model ready", name)
        except Exception as exc:  # noqa: BLE001 - warm-up must never crash boot
            logger.warning("warm-up: failed to load %s model: %s", name, exc)

    return registry.health_status()
