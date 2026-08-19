from typing import Any

from fastapi import APIRouter

from app.flags.runner import run_flags
from app.scoring.report_builder import build_report

router = APIRouter()


@router.post("/report")
def report(claims: list[dict[str, Any]]) -> dict[str, str]:
    for claim in claims:
        claim["flags"] = run_flags(
            claim,
            known_references=set(),
            retracted_references=set(),
        )

    markdown = build_report(claims)

    return {
        "report": markdown,
    }