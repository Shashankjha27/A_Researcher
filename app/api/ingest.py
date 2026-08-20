from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.pipeline.ingest import ingest_paper
from app.store.doc_store import DocStore

router = APIRouter(tags=["ingestion"])

DATA_IN = Path("data/in")
DATA_IN.mkdir(parents=True, exist_ok=True)


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name


@router.post("/ingest")
def ingest(
    file: UploadFile = File(...),  # noqa: B008
    paper_id: str = Form(...),
    title: str = Form(...),
    authors: str = Form(""),
    year: int = Form(...),
    doi: str | None = Form(default=None),
    journal: str | None = Form(default=None),
    funding_source: str | None = Form(default=None),
) -> dict[str, str]:
    if not file.filename:
        raise HTTPException(
            status_code=422,
            detail="No filename provided",
        )

    author_list = [
        a.strip() for a in authors.split(",") if a.strip()
    ]

    filename = _safe_filename(file.filename)
    save_path = DATA_IN / f"{paper_id}_{filename}"

    content = file.file.read()
    save_path.write_bytes(content)

    try:
        paper = ingest_paper(
            save_path,
            paper_id=paper_id,
            title=title.strip(),
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
