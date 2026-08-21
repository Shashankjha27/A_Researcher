from __future__ import annotations

import re
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.pipeline.ingest import ingest_paper
from app.pipeline.metadata import extract_metadata
from app.sources.arxiv import (
    download_arxiv_pdf,
    fetch_arxiv_metadata,
    parse_arxiv_id,
)
from app.store.doc_store import DocStore

router = APIRouter(tags=["ingestion"])

DATA_IN = Path("data/in")
DATA_IN.mkdir(parents=True, exist_ok=True)


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name


class IngestUrlRequest(BaseModel):
    url: str
    paper_id: str | None = None


@router.post("/ingest/url")
def ingest_from_url(request: IngestUrlRequest) -> dict[str, str]:
    paper_id = request.paper_id or f"paper-{uuid.uuid4().hex[:12]}"

    try:
        arxiv_id = parse_arxiv_id(request.url)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    try:
        metadata = fetch_arxiv_metadata(arxiv_id)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"arXiv lookup failed: {exc}",
        ) from exc

    safe_id = _safe_filename(f"{arxiv_id}.pdf")
    save_path = DATA_IN / f"{paper_id}_{safe_id}"

    try:
        download_arxiv_pdf(arxiv_id, save_path)
        paper = ingest_paper(
            save_path,
            paper_id=paper_id,
            title=metadata["title"],
            authors=metadata["authors"],
            year=metadata["year"],
            doi=metadata.get("doi"),
            journal=metadata.get("journal"),
        )
    except (httpx.HTTPError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=502 if isinstance(exc, httpx.HTTPError) else 400,
            detail=str(exc),
        ) from exc

    store = DocStore()
    store.save("papers", paper)

    return {"paper_id": paper.paper_id}


@router.post("/ingest")
def ingest(
    file: UploadFile = File(...),  # noqa: B008
    paper_id: str = Form(...),
    title: str | None = Form(default=None),
    authors: str | None = Form(default=None),
    year: int | None = Form(default=None),
    doi: str | None = Form(default=None),
    journal: str | None = Form(default=None),
    funding_source: str | None = Form(default=None),
) -> dict[str, str]:
    if not file.filename:
        raise HTTPException(
            status_code=422,
            detail="No filename provided",
        )

    filename = _safe_filename(file.filename)
    save_path = DATA_IN / f"{paper_id}_{filename}"

    content = file.file.read()
    save_path.write_bytes(content)

    resolved_title = (title or "").strip()
    author_list = [
        a.strip() for a in (authors or "").split(",") if a.strip()
    ]

    if not resolved_title or not author_list or year is None:
        try:
            extracted = extract_metadata(save_path)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"metadata extraction failed: {exc}",
            ) from exc

        resolved_title = resolved_title or extracted["title"]
        author_list = author_list or extracted["authors"]
        year = year if year is not None else extracted["year"]

    try:
        paper = ingest_paper(
            save_path,
            paper_id=paper_id,
            title=resolved_title,
            authors=author_list,
            year=year,
            doi=doi,
            journal=journal,
            funding_source=funding_source,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    store = DocStore()
    store.save("papers", paper)

    return {"paper_id": paper.paper_id}
