from pathlib import Path

import pytest

from app.pipeline.ingest import (
    ingest_paper,
    normalize_text,
    read_paper,
    split_sections,
    split_sentences,
)
from app.schemas import SourceType


def test_normalize_text():
    text = (
        "This is a scien-\n"
        "tific paper.\r\n"
        "\r\n"
        "This   has   extra   spaces.\n\n\n"
        "Next paragraph."
    )

    result = normalize_text(text)

    assert result == (
        "This is a scientific paper.\n\n"
        "This has extra spaces.\n\n"
        "Next paragraph."
    )


def test_split_sentences():
    text = (
        "This is the first sentence. "
        "This is the second sentence. "
        "This is the third sentence."
    )

    sentences = split_sentences(text)

    assert len(sentences) == 3

    for sentence, start, end in sentences:
        assert text[start:end] == sentence


def test_split_sentences_handles_abbreviations():
    text = (
        "This result is shown in Fig. 2. "
        "The result is significant. "
        "For example, the model performs well."
    )

    sentences = split_sentences(text)

    assert len(sentences) == 3
    assert sentences[0][0] == "This result is shown in Fig. 2."
    assert sentences[1][0] == "The result is significant."


def test_split_sentences_not_confused_by_words_ending_in_abbrev_prefix():
    text = (
        "The treatment significantly improves recovery in the control "
        "group. However, a follow-up analysis disagrees."
    )

    sentences = split_sentences(text)

    assert len(sentences) == 2
    assert sentences[0][0].endswith("control group.")
    assert sentences[1][0] == "However, a follow-up analysis disagrees."


def test_split_sentences_handles_decimal_numbers():
    text = (
        "The model achieved 92.5% accuracy. "
        "This result was reproduced."
    )

    sentences = split_sentences(text)

    assert len(sentences) == 2
    assert sentences[0][0] == "The model achieved 92.5% accuracy."
    assert sentences[1][0] == "This result was reproduced."


def test_split_sentences_handles_tail_without_punctuation():
    text = "This sentence has no final punctuation"

    sentences = split_sentences(text)

    assert len(sentences) == 1

    sentence, start, end = sentences[0]

    assert sentence == text
    assert start == 0
    assert end == len(text)


def test_sentence_offsets_are_exact():
    text = (
        "First sentence. "
        "Second sentence. "
        "Third sentence."
    )

    sentences = split_sentences(text)

    for sentence, start, end in sentences:
        assert text[start:end] == sentence


def test_split_sections():
    text = (
        "Abstract\n"
        "This is the abstract.\n\n"
        "Introduction\n"
        "This is the introduction.\n\n"
        "Methods\n"
        "This is the methods section.\n\n"
        "Results\n"
        "These are the results."
    )

    sections = split_sections(text)

    names = [section[0] for section in sections]

    assert names == [
        "abstract",
        "introduction",
        "methods",
        "results",
    ]


def test_split_sections_falls_back_to_fulltext():
    text = "This document has no recognized section headers."

    sections = split_sections(text)

    assert len(sections) == 1

    section, body, start, end = sections[0]

    assert section == "fulltext"
    assert body == text
    assert start == 0
    assert end == len(text)


def test_section_offsets_are_exact():
    text = (
        "Abstract\n"
        "This is the abstract.\n\n"
        "Methods\n"
        "This is the methods section."
    )

    sections = split_sections(text)

    for _, body, start, end in sections:
        assert text[start:end] == body


def test_read_txt(tmp_path: Path):
    path = tmp_path / "paper.txt"

    path.write_text(
        "This is a research paper.\n\n"
        "It contains two sentences.",
        encoding="utf-8",
    )

    result = read_paper(path)

    assert result == (
        "This is a research paper.\n\n"
        "It contains two sentences."
    )


def test_read_markdown(tmp_path: Path):
    path = tmp_path / "paper.md"

    path.write_text(
        "# Research Paper\n\n"
        "This is the introduction.",
        encoding="utf-8",
    )

    result = read_paper(path)

    assert "# Research Paper" in result
    assert "This is the introduction." in result


def test_unsupported_file_type(tmp_path: Path):
    path = tmp_path / "paper.docx"
    path.write_text("test", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported file type"):
        read_paper(path)


def test_missing_file():
    path = Path("does-not-exist.txt")

    with pytest.raises(FileNotFoundError):
        read_paper(path)


def test_empty_file(tmp_path: Path):
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="no extractable text"):
        read_paper(path)


def test_ingest_paper(tmp_path: Path):
    path = tmp_path / "paper.txt"

    path.write_text(
        "Abstract\n"
        "This paper studies a useful method.\n\n"
        "Methods\n"
        "We evaluate the method on a dataset.\n\n"
        "Results\n"
        "The method improves accuracy.",
        encoding="utf-8",
    )

    paper = ingest_paper(
        path,
        paper_id="paper-001",
        title="Example Research Paper",
        authors=["Alice", "Bob"],
        year=2026,
    )

    assert paper.paper_id == "paper-001"
    assert paper.title == "Example Research Paper"
    assert paper.authors == ["Alice", "Bob"]
    assert paper.year == 2026
    assert paper.source == SourceType.TEXT
    assert paper.path == str(path)
    assert paper.ingested_at is not None

    assert len(paper.blocks) == 3
    assert paper.blocks[0].section == "abstract"
    assert paper.blocks[1].section == "methods"
    assert paper.blocks[2].section == "results"


def test_ingest_paper_with_metadata(tmp_path: Path):
    path = tmp_path / "paper.md"

    path.write_text(
        "Introduction\n"
        "This paper introduces a new method.",
        encoding="utf-8",
    )

    paper = ingest_paper(
        path,
        paper_id="paper-002",
        title="New Method",
        authors=["Researcher"],
        year=2026,
        doi="10.1234/example",
        journal="Example Journal",
        funding_source="Example Foundation",
    )

    assert paper.doi == "10.1234/example"
    assert paper.journal == "Example Journal"
    assert paper.funding_source == "Example Foundation"


def test_ingest_paper_missing_file():
    with pytest.raises(FileNotFoundError):
        ingest_paper(
            "missing-paper.pdf",
            paper_id="paper-003",
            title="Missing Paper",
            authors=[],
            year=2026,
        )


def test_ingest_paper_unsupported_file(tmp_path: Path):
    path = tmp_path / "paper.docx"
    path.write_text("not supported", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported file type"):
        ingest_paper(
            path,
            paper_id="paper-004",
            title="Unsupported",
            authors=[],
            year=2026,
        )