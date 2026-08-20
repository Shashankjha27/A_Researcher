from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.pipeline.run import run_pipeline

router = APIRouter(tags=["ui"])

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

DATA_IN = PROJECT_ROOT / "data" / "in"
DATA_IN.mkdir(parents=True, exist_ok=True)

_latest_results: list[dict[str, Any]] = []


def set_latest_results(results: list[dict[str, Any]]) -> None:
    global _latest_results
    _latest_results = results


def _build_contradictions(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    contradictions = []

    for result in results:
        claims = {
            claim.get("claim_id"): claim
            for claim in result.get("claims", [])
        }

        for pair in result.get("pair_verdicts", []):
            relation = str(pair.get("relation", "")).upper()

            if relation != "CONTRADICTION":
                continue

            left_id = pair.get("claim_id_a")
            right_id = pair.get("claim_id_b")

            left_claim = claims.get(left_id)
            right_claim = claims.get(right_id)

            if left_claim is None or right_claim is None:
                continue

            contradictions.append(
                {
                    "claim_a": left_claim,
                    "claim_b": right_claim,
                    "verdict": relation,
                    "nli_probability": pair.get("nli_probability"),
                }
            )

    return contradictions


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)

    if not name.lower().endswith(".pdf"):
        name += ".pdf"

    return name


@router.post("/verify/upload")
def upload_and_verify(
    file: UploadFile = File(...),
    title: str = Form(...),
    authors: str = Form(""),
    year: int = Form(...),
    paper_id: str = Form(""),
) -> RedirectResponse:
    if not file.filename:
        return RedirectResponse(
            url="/report?error=No+PDF+selected",
            status_code=303,
        )

    if not file.filename.lower().endswith(".pdf"):
        return RedirectResponse(
            url="/report?error=Only+PDF+files+are+supported",
            status_code=303,
        )

    filename = _safe_filename(file.filename)

    if not paper_id.strip():
        paper_id = f"paper-{uuid4().hex[:12]}"

    save_path = DATA_IN / f"{paper_id}_{filename}"

    content = file.file.read()
    save_path.write_bytes(content)

    author_list = [
        author.strip()
        for author in authors.split(",")
        if author.strip()
    ]

    result = run_pipeline(
        save_path,
        paper_id=paper_id,
        title=title.strip(),
        authors=author_list,
        year=year,
    )

    set_latest_results([result])

    return RedirectResponse(
        url="/report",
        status_code=303,
    )


@router.get("/report")
def report_page(request: Request) -> Any:
    results = _latest_results

    claims = []
    flags = []
    reports = []

    for result in results:
        claims.extend(result.get("claims", []))
        reports.append(result.get("report"))

        for claim in result.get("claims", []):
            claim_flags = claim.get("flags", [])

            if isinstance(claim_flags, list):
                flags.extend(claim_flags)

    contradictions = _build_contradictions(results)

    return templates.TemplateResponse(
        request=request,
        name="report.html",
        context={
            "title": "A_Researcher Report",
            "report": reports,
            "claims": claims,
            "flags": flags,
            "contradictions": contradictions,
        },
    )