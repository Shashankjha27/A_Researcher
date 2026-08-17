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

_SENTENCE_END = re.compile(
    r"""[.!?](?:["'”’)\]]+)?(?=\s|$)"""
)

_SECTION_NAMES = (
    r"abstract|"
    r"introduction|"
    r"background|"
    r"related\s+work|"
    r"literature\s+review|"
    r"methodology|"
    r"methods?|"
    r"materials?\s+and\s+methods?|"
    r"experimental\s+setup|"
    r"experimental\s+method|"
    r"experiments?|"
    r"results?|"
    r"discussion|"
    r"results?\s+and\s+discussion|"
    r"conclusions?|"
    r"future\s+work|"
    r"limitations?|"
    r"acknowledg(?:e)?ments?|"
    r"references"
)

_SECTION_HEADER_RE = re.compile(
    rf"""
    ^
    (?P<header>
        (?:
            (?P<number>
                (?:\d+(?:\.\d+)*)[\.\)]?
                |
                (?:[IVXLCDM]+)[\.\)]
                |
                (?:[A-Z])[\.\)]
            )
            \s*
        )?
        (?P<name>{_SECTION_NAMES})
        (?P<separator>
            \s*(?:[—–-]\s*|:\s*)
        )?
    )
    (?=
        \s*$ |
        \s+[A-Z0-9] |
        \s*
    )
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE,
)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    text = re.sub(
        r"(?<=\w)-\n(?=\w)",
        "",
        text,
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def _is_abbreviation(
    text: str,
    punctuation_position: int,
) -> bool:
    prefix = text[:punctuation_position + 1].lower()

    return any(
        prefix.endswith(abbreviation)
        for abbreviation in _ABBREVS
    )


def split_sentences(
    text: str,
) -> list[tuple[str, int, int]]:
    sentences: list[tuple[str, int, int]] = []

    start = 0

    for match in _SENTENCE_END.finditer(text):
        punctuation_position = match.start()

        if _is_abbreviation(
            text,
            punctuation_position,
        ):
            continue

        end = match.end()
        sentence_start = start

        while (
            sentence_start < end
            and text[sentence_start].isspace()
        ):
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

    sentence_start = start

    while (
        sentence_start < len(text)
        and text[sentence_start].isspace()
    ):
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


def _normalize_section_name(
    name: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        name.strip().lower(),
    )


def _find_section_header(
    line: str,
) -> re.Match[str] | None:
    match = _SECTION_HEADER_RE.match(line)

    if not match:
        return None

    consumed = match.group(0).strip()
    remainder = line[match.end():].strip()

    if remainder and len(consumed) < 3:
        return None

    return match


def split_sections(
    text: str,
) -> list[tuple[str, str, int, int]]:
    matches: list[tuple[str, int, int]] = []

    for line_match in re.finditer(
        r"(?m)^[^\n]+",
        text,
    ):
        line = line_match.group(0).strip()

        if not line:
            continue

        header_match = _find_section_header(line)

        if not header_match:
            continue

        section_name = _normalize_section_name(
            header_match.group("name")
        )

        header_start = (
            line_match.start()
            + len(line_match.group(0))
            - len(line_match.group(0).lstrip())
        )

        header_end = (
            line_match.start()
            + header_match.end()
        )

        matches.append(
            (
                section_name,
                header_start,
                header_end,
            )
        )

    if not matches:
        return [
            (
                "fulltext",
                text,
                0,
                len(text),
            )
        ]

    sections: list[
        tuple[str, str, int, int]
    ] = []

    first_header_start = matches[0][1]

    if first_header_start > 0:
        prefix = text[:first_header_start]

        leading = len(prefix) - len(
            prefix.lstrip()
        )
        trailing = len(prefix) - len(
            prefix.rstrip()
        )

        start = leading
        end = len(prefix) - trailing

        if start < end:
            sections.append(
                (
                    "frontmatter",
                    text[start:end],
                    start,
                    end,
                )
            )

    for index, (
        section_name,
        header_start,
        header_end,
    ) in enumerate(matches):
        body_start = header_end

        body_end = (
            matches[index + 1][1]
            if index + 1 < len(matches)
            else len(text)
        )

        raw_body = text[body_start:body_end]

        leading = len(raw_body) - len(
            raw_body.lstrip()
        )
        trailing = len(raw_body) - len(
            raw_body.rstrip()
        )

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


def read_text(
    path: Path,
) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def read_pdf(
    path: Path,
) -> str:
    try:
        reader = PdfReader(str(path))

        if reader.is_encrypted:
            try:
                decrypted = reader.decrypt("")

                if not decrypted:
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


def read_paper(
    path: str | Path,
) -> str:
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


def _build_blocks(
    text: str,
) -> list[Block]:
    blocks: list[Block] = []

    for (
        section,
        body,
        start,
        end,
    ) in split_sections(text):
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
    path = Path(path)

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