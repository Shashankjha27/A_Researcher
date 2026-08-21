"""arXiv as a direct paper source.

Fetches metadata from the arXiv Atom API and downloads the PDF, so a
paper can be ingested from its public identifier without manual data
entry.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}"

_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_ARXIV_NS = "{http://arxiv.org/schemas/atom}"

_ID_PATTERN = re.compile(
    r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?",
)

_REQUEST_TIMEOUT = 30.0
_DOWNLOAD_TIMEOUT = 120.0


def parse_arxiv_id(source: str) -> str:
    """Extract an arXiv identifier from a URL or bare id string."""
    match = _ID_PATTERN.search(source.strip())

    if not match:
        raise ValueError(f"Not a valid arXiv id or URL: {source!r}")

    return match.group(0)


def parse_arxiv_atom(xml_text: str) -> dict[str, Any]:
    """Parse the Atom entry returned by the arXiv API into metadata."""
    root = ET.fromstring(xml_text)
    entry = root.find(f"{_ATOM_NS}entry")

    if entry is None:
        raise ValueError("arXiv API returned no entry")

    title = " ".join((entry.findtext(f"{_ATOM_NS}title") or "").split())

    authors = [
        name
        for author in entry.findall(f"{_ATOM_NS}author")
        if (name := (author.findtext(f"{_ATOM_NS}name") or "").strip())
    ]

    published = entry.findtext(f"{_ATOM_NS}published") or ""
    year_match = re.match(r"(\d{4})", published)
    year = (
        int(year_match.group(1))
        if year_match
        else datetime.now(timezone.utc).year
    )

    return {
        "title": title,
        "authors": authors,
        "year": year,
        "doi": (entry.findtext(f"{_ARXIV_NS}doi") or "").strip() or None,
        "journal": (
            entry.findtext(f"{_ARXIV_NS}journal_ref") or ""
        ).strip()
        or None,
    }


def fetch_arxiv_metadata(arxiv_id: str) -> dict[str, Any]:
    """Look up title, authors, and year for an arXiv identifier."""
    response = httpx.get(
        ARXIV_API_URL,
        params={"id_list": arxiv_id},
        timeout=_REQUEST_TIMEOUT,
        follow_redirects=True,
    )
    response.raise_for_status()

    return parse_arxiv_atom(response.text)


def download_arxiv_pdf(arxiv_id: str, dest: Path) -> Path:
    """Download the latest PDF version of a paper to ``dest``."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    with httpx.stream(
        "GET",
        ARXIV_PDF_URL.format(arxiv_id=arxiv_id),
        timeout=_DOWNLOAD_TIMEOUT,
        follow_redirects=True,
    ) as response:
        response.raise_for_status()

        with dest.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)

    return dest
