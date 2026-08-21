from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.store.doc_store import DocStore

router = APIRouter(tags=["papers"])


@router.get("/papers")
def list_papers() -> list[dict[str, Any]]:
    store = DocStore()

    latest: dict[str, Any] = {}

    for paper in store.all("papers"):
        latest[paper.paper_id] = paper

    items: list[dict[str, Any]] = []

    for paper in latest.values():
        claim_count = len(store.query("claims", paper_id=paper.paper_id))

        items.append(
            {
                "paper_id": paper.paper_id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "path": paper.path,
                "funding_source": paper.funding_source,
                "retraction_status": paper.retraction_status.value,
                "claim_count": claim_count,
            }
        )

    return items


@router.get("/papers/{paper_id}/blocks")
def get_paper_blocks(paper_id: str) -> dict[str, Any]:
    store = DocStore()

    paper = store.get("papers", paper_id)

    if paper is None:
        raise HTTPException(
            status_code=404,
            detail=f"Paper not found: {paper_id}",
        )

    return {
        "paper_id": paper.paper_id,
        "title": paper.title,
        "blocks": [
            {
                "section": block.section,
                "text": block.text,
                "start_offset": block.start_offset,
                "end_offset": block.end_offset,
            }
            for block in paper.blocks
        ],
    }
