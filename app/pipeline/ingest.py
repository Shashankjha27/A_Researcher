from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.schemas import Block, Paper, SourceType

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}

_ABBREVS = {
    "e.g.",
    "i.e.",
    "et al.",
    "fig.",
    "figs.",
    "vs.",
    "approx.",
    "cf.",
    "dr.",
    "mr.",
    "mrs.",
    "prof.",
    "eq.",
    "eqs.",
    "ref.",
    "refs.",
    "no.",
    "vol.",
    "pp.",
    "p.",
    "et seq.",
}

_MAX_ABBREV_LEN = max(len(a) for a in _ABBREVS)

_SENTENCE_END = re.compile(
    r"""(?<!\d)[.!?](?:["'”’)\]]+)?(?=\s|$)"""
)

_SECTION_HEADERS = re.compile(
    r"""
    ^\s*
    (?P<section>
        abstract|
        introduction|
        background|
        related\s+work|
        methods?|
        materials\s+and\s+methods|
        results?|
        discussion|
        conclusions?|
        acknowledg(?:e)?ments?|
        references
    )
    \s*$
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE,
)


def normalize_text(text: str) -> str:
    """
    Normalize common TXT/Markdown/PDF extraction artifacts.

    The returned text is the canonical text used for all offsets.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove soft hyphenation caused by PDF line wrapping.
    # Example: "scien-\ntific" -> "scientific"
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)

    # Normalize horizontal whitespace while preserving newlines.
    text = re.sub(r"[ \t]+", " ", text)

    # Avoid excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _is_abbreviation(text: str, punctuation_position: int) -> bool:
    """
    Check whether a sentence-ending punctuation mark belongs
    to a known abbreviation.

    Only looks at a small bounded window ending at the punctuation mark,
    so this stays O(1) regardless of document length.
    """
    window_start = max(0, punctuation_position + 1 - _MAX_ABBREV_LEN)
    prefix = text[window_start:punctuation_position + 1].lower()

    return any(
        prefix.endswith(abbreviation)
        for abbreviation in _ABBREVS
    )


def split_sentences(text: str) -> list[tuple[str, int, int]]:
    """
    Split text into sentences.

    Returns:
        (sentence_text, start_offset, end_offset)

    Offsets are relative to the supplied text and satisfy:

        text[start_offset:end_offset] == sentence_text
    """
    sentences: list[tuple[str, int, int]] = []

    start = 0

    for match in _SENTENCE_END.finditer(text):
        punctuation_position = match.start()

        if _is_abbreviation(text, punctuation_position):
            continue

        end = match.end()

        # Include closing punctuation/quotes but not leading whitespace.
        sentence_start = start

        while sentence_start < end and text[sentence_start].isspace():
            sentence_start += 1

        sentence = text[sentence_start:end]

        if sentence:
            sentences.append(
                (
                    sentence,
                    sentence_start,
                    end,
                )
            )

        start = end

    # Capture remaining text that does not end in punctuation.
    sentence_start = start

    while sentence_start < len(text) and text[sentence_start].isspace():
        sentence_start += 1

    if sentence_start < len(text):
        sentences.append(
            (
                text[sentence_start:],
                sentence_start,
                len(text),
            )
        )

    return sentences


def split_sections(text: str) -> list[tuple[str, str, int, int]]:
    """
    Split a document into known scientific sections.

    Returns:
        (section_name, body, start_offset, end_offset)

    Offsets are relative to the normalized document text.

    If no recognized section headers are found, the entire document
    becomes one 'fulltext' section.
    """
    matches = list(_SECTION_HEADERS.finditer(text))

    if not matches:
        return [
            (
                "fulltext",
                text,
                0,
                len(text),
            )
        ]

    sections: list[tuple[str, str, int, int]] = []

    # Preserve any content before the first recognized header.
    if matches[0].start() > 0:
        prefix = text[:matches[0].start()]
        prefix_start = 0
        prefix_end = len(prefix)

        stripped = prefix.strip()

        if stripped:
            leading = len(prefix) - len(prefix.lstrip())
            trailing = len(prefix) - len(prefix.rstrip())

            start = prefix_start + leading
            end = prefix_end - trailing

            sections.append(
                (
                    "frontmatter",
                    text[start:end],
                    start,
                    end,
                )
            )

    for index, match in enumerate(matches):
        section_name = re.sub(
            r"\s+",
            " ",
            match.group("section").strip().lower(),
        )

        body_start = match.end()
        body_end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )

        raw_body = text[body_start:body_end]

        # Make offsets correspond exactly to the stripped body.
        leading = len(raw_body) - len(raw_body.lstrip())
        trailing = len(raw_body) - len(raw_body.rstrip())

        start = body_start + leading
        end = body_end - trailing

        if start >= end:
            continue

        sections.append(
            (
                section_name,
                text[start:end],
                start,
                end,
            )
        )

    return sections


def read_text(path: Path) -> str:
    """Read TXT/Markdown input."""
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def read_pdf(path: Path) -> str:
    """Extract text from a PDF using pypdf."""
    try:
        reader = PdfReader(str(path))

        if reader.is_encrypted:
            try:
                result = reader.decrypt("")

                if not result:
                    raise ValueError(
                        f"encrypted PDF, cannot read: {path}"
                    )

            except Exception as exc:
                raise ValueError(
                    f"encrypted PDF, cannot read: {path}"
                ) from exc

        pages: list[str] = []

        for page in reader.pages:
            page_text = page.extract_text() or ""

            if page_text.strip():
                pages.append(page_text)

        return "\n\n".join(pages)

    except PdfReadError as exc:
        raise ValueError(
            f"corrupted or unreadable PDF: {path}"
        ) from exc


def read_paper(path: str | Path) -> str:
    """
    Read and normalize a supported paper file.

    Supported:
        .txt
        .md
        .pdf

    Validates existence, extension, and non-empty content — this is the
    single source of truth for input validation; callers should not
    duplicate these checks.
    """
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(
            f"no such paper: {path}"
        )

    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(
            sorted(SUPPORTED_EXTENSIONS)
        )

        raise ValueError(
            f"unsupported file type '{suffix}'. "
            f"Expected: {supported}"
        )

    if suffix == ".pdf":
        raw = read_pdf(path)
    else:
        raw = read_text(path)

    normalized = normalize_text(raw)

    if not normalized:
        raise ValueError(
            f"no extractable text in: {path}"
        )

    return normalized


def _build_blocks(text: str) -> list[Block]:
    """
    Convert normalized document text into Paper blocks.

    Each block keeps exact document offsets.
    """
    blocks: list[Block] = []

    for section, body, start, end in split_sections(text):
        blocks.append(
            Block(
                section=section,
                text=body,
                start_offset=start,
                end_offset=end,
            )
        )

    return blocks


def ingest_paper(
    path: str | Path,
    paper_id: str,
    *,
    title: str,
    authors: list[str],
    year: int,
    source: SourceType | None = None,
    doi: str | None = None,
    journal: str | None = None,
    funding_source: str | None = None,
) -> Paper:
    """
    Ingest a paper into the Phase 1 Paper schema.

    Pipeline:

        file
          ↓
        read + validate (read_paper)
          ↓
        normalize
          ↓
        section detection
          ↓
        blocks with exact offsets
          ↓
        Paper
    """
    path = Path(path)

    # read_paper is the single source of truth for existence/extension/
    # non-empty validation — no need to duplicate those checks here.
    text = read_paper(path)

    suffix = path.suffix.lower()
    resolved_source = source or (
        SourceType.PDF
        if suffix == ".pdf"
        else SourceType.TEXT
    )

    blocks = _build_blocks(text)

    if not blocks:
        raise ValueError(
            f"no document blocks could be created: {path}"
        )

    return Paper(
        paper_id=paper_id,
        title=title,
        authors=authors,
        year=year,
        source=resolved_source,
        path=str(path),
        ingested_at=datetime.now(timezone.utc),
        doi=doi,
        journal=journal,
        funding_source=funding_source,
        blocks=blocks,
    )