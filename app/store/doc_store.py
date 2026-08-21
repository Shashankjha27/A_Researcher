from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.schemas import (
    Claim,
    ClaimPairVerdict,
    DebateRecord,
    Flag,
    FlagReview,
    Paper,
    VerdictOverride,
)
from config import DATA_OUT

ENTITY_MODELS: dict[str, type[BaseModel]] = {
    "papers": Paper,
    "claims": Claim,
    "pair_verdicts": ClaimPairVerdict,
    "flags": Flag,
    "debates": DebateRecord,
    "verdict_overrides": VerdictOverride,
    "flag_reviews": FlagReview,
}

ID_FIELDS: dict[str, str] = {
    "papers": "paper_id",
    "claims": "claim_id",
    "pair_verdicts": "pair_id",
    "flags": "flag_id",
    "debates": "debate_id",
    "verdict_overrides": "override_id",
    "flag_reviews": "review_id",
}


class DocStore:
    def __init__(self, base_dir: str | Path = DATA_OUT) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _check_entity(self, entity: str) -> None:
        if entity not in ENTITY_MODELS:
            raise KeyError(f"unknown entity: {entity!r}")

    def _path(self, entity: str) -> Path:
        self._check_entity(entity)
        return self.base_dir / f"{entity}.jsonl"

    def _iter(self, entity: str) -> Iterable[BaseModel]:
        path = self._path(entity)

        if not path.exists():
            return

        model = ENTITY_MODELS[entity]

        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield model.model_validate_json(line)

    def save(self, entity: str, doc: BaseModel) -> None:
        path = self._path(entity)

        with path.open("a", encoding="utf-8") as fh:
            fh.write(doc.model_dump_json() + "\n")

    def all(self, entity: str) -> list[BaseModel]:
        return list(self._iter(entity))

    def get(self, entity: str, doc_id: str) -> BaseModel | None:
        self._check_entity(entity)

        id_field = ID_FIELDS[entity]

        # The store is append-only: the last row for an id is the
        # latest version of the document.
        latest: BaseModel | None = None

        for doc in self._iter(entity):
            if getattr(doc, id_field) == doc_id:
                latest = doc

        return latest

    def query(self, entity: str, **filters: Any) -> list[BaseModel]:
        self._check_entity(entity)

        return [
            doc
            for doc in self._iter(entity)
            if all(
                getattr(doc, key) == value
                for key, value in filters.items()
            )
        ]