from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from app.llm.client import get_llm_call

logger = logging.getLogger(__name__)

_YEAR_PATTERN = re.compile(r"\b((?:19|20)\d{2})\b")

_PROMPT = """You are extracting bibliographic metadata from the beginning of a scientific paper.

Return ONLY a JSON object. No prose, no markdown fences.

Exact shape:
{{"title": string, "authors": [string, ...], "year": integer or null}}

- "title": the paper's full title as written (not the filename).
- "authors": full author names in order, [] if none are visible.
- "year": publication year if visible, otherwise null.

PAPER TEXT:
{paper_text}
"""


def _clean_title(raw: str) -> str:
    title = re.sub(r"\s+", " ", raw).strip(" .-")

    if len(title) < 4:
        return ""

    return title


def _split_authors(raw: str) -> list[str]:
    parts = re.split(r"\s*(?:,| and |;|\band\b)\s*", raw.strip())

    return [
        re.sub(r"\s+", " ", part).strip(" .")
        for part in parts
        if part and len(part.strip()) > 2
    ]


def _metadata_from_pdf(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "title": "",
        "authors": [],
        "year": None,
        "first_page_text": "",
    }

    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001
        logger.warning("pypdf could not read %s: %s", path, exc)
        return result

    meta = reader.metadata or {}

    raw_title = str(meta.get("/Title") or "").strip()

    if raw_title and not raw_title.lower().endswith(".pdf"):
        result["title"] = _clean_title(raw_title)

    raw_author = str(meta.get("/Author") or "").strip()

    if raw_author:
        result["authors"] = _split_authors(raw_author)

    created = str(meta.get("/CreationDate") or "")
    match = _YEAR_PATTERN.search(created)

    if match:
        result["year"] = int(match.group(1))

    try:
        if reader.pages:
            result["first_page_text"] = (
                reader.pages[0].extract_text() or ""
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "could not extract first page text: %s",
            exc,
        )

    return result


def _metadata_from_text(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "title": "",
        "authors": [],
        "year": None,
    }

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    candidates = [
        line
        for line in lines[:6]
        if 10 <= len(line) <= 300
        and not line.lower().startswith(("arxiv", "doi:", "http"))
    ]

    if candidates:
        result["title"] = _clean_title(max(candidates, key=len))

    year_match = _YEAR_PATTERN.search(text[:2000])

    if year_match:
        result["year"] = int(year_match.group(1))

    abstract_index = next(
        (
            index
            for index, line in enumerate(lines[:40])
            if line.lower().startswith("abstract")
        ),
        None,
    )

    if abstract_index and abstract_index > 0:
        byline = lines[abstract_index - 1]

        if 3 < len(byline) < 400 and "@" not in byline:
            authors = _split_authors(byline)

            if 0 < len(authors) <= 15:
                result["authors"] = authors

    return result


def _metadata_from_llm(text: str) -> dict[str, Any]:
    empty: dict[str, Any] = {
        "title": "",
        "authors": [],
        "year": None,
    }

    snippet = text[:2000].strip()

    if not snippet:
        return empty

    try:
        llm_call = get_llm_call()
        raw = llm_call(_PROMPT.format(paper_text=snippet))
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM metadata extraction failed: %s", exc)
        return empty

    cleaned = raw.strip().removeprefix("```json").strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("LLM metadata was not valid JSON")
        return empty

    title = _clean_title(str(data.get("title") or ""))
    authors_raw = data.get("authors") or []
    authors = [
        str(name).strip()
        for name in authors_raw
        if str(name).strip()
    ]
    year = data.get("year")

    return {
        "title": title,
        "authors": authors[:25],
        "year": int(year) if isinstance(year, (int, float)) else None,
    }


def extract_metadata(path: str | Path) -> dict[str, Any]:
    """
    Extract title/authors/year from paper content, not its filename.

    Three tiers: embedded PDF metadata, first-page text heuristics,
    then an LLM call for anything still missing. Always returns a
    usable title (filename stem as last resort) and year.
    """
    path = Path(path)

    pdf_meta = _metadata_from_pdf(path)
    text_meta = _metadata_from_text(pdf_meta["first_page_text"])

    title = pdf_meta["title"] or text_meta["title"]
    authors = pdf_meta["authors"] or text_meta["authors"]
    year = pdf_meta["year"] or text_meta["year"]

    if not title or not authors or year is None:
        llm_meta = _metadata_from_llm(pdf_meta["first_page_text"])

        title = title or llm_meta["title"]
        authors = authors or llm_meta["authors"]
        year = year or llm_meta["year"]

    if not title:
        title = _clean_title(path.stem.replace("_", " "))

    if year is None:
        year = datetime.now(timezone.utc).year

    return {
        "title": title,
        "authors": authors,
        "year": int(year),
    }
