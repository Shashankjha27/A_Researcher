"""Import the checked-in demo fixture into the store when missing.

The demo report (paper-demo-golden) ships as JSONL fixtures under
data/demo/ so judges can open a fully verified report instantly,
without running an LLM extraction. ensure_demo_data() is called at
app startup and appends the fixture rows only if the demo paper is
not already present (the store is append-only, so this is a no-op
on every subsequent boot).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.store.doc_store import ENTITY_MODELS, DocStore

logger = logging.getLogger(__name__)

DEMO_PAPER_ID = "paper-demo-golden"

DEMO_DIR = Path("data/demo")

_FIXTURE_ENTITIES = ("papers", "claims", "pair_verdicts")


def _load_fixtures() -> dict[str, list[dict]]:
    fixtures: dict[str, list[dict]] = {}

    for entity in _FIXTURE_ENTITIES:
        path = DEMO_DIR / f"demo_fixture_{entity}.jsonl"

        if not path.is_file():
            logger.warning("demo fixture missing: %s", path)

            fixtures[entity] = []

            continue

        fixtures[entity] = [
            json.loads(line)
            for line in path.read_text().splitlines()
            if line.strip()
        ]

    return fixtures


def ensure_demo_data(store: DocStore | None = None) -> bool:
    """Seed the demo paper from fixtures. Returns True if seeded."""

    store = store or DocStore()

    existing = store.query("papers", paper_id=DEMO_PAPER_ID)

    if existing:
        return False

    fixtures = _load_fixtures()

    papers = fixtures.get("papers", [])

    if not papers:
        logger.warning("demo fixture has no paper row; skipping seed")

        return False

    for entity in _FIXTURE_ENTITIES:
        model_cls = ENTITY_MODELS[entity]

        for row in fixtures.get(entity, []):
            store.save(entity, model_cls.model_validate(row))

    claim_count = len(fixtures.get("claims", []))

    logger.info(
        "seeded demo paper %s (%d claims)",
        DEMO_PAPER_ID,
        claim_count,
    )

    return True
