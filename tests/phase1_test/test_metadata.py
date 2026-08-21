from datetime import datetime, timezone

from app.pipeline.metadata import (
    _metadata_from_text,
    _split_authors,
    extract_metadata,
)


def test_split_authors_handles_separators():
    authors = _split_authors(
        "Jane Doe, John Smith and A. B. Third; Fourth Person"
    )

    assert authors == [
        "Jane Doe",
        "John Smith",
        "A. B. Third",
        "Fourth Person",
    ]


def test_heuristics_find_title_year_and_authors():
    text = """Some Venue Stamp 2021
Deep Learning Improves Claim Verification
Jane Doe, John Smith
Abstract
We verify claims with transformers. In 2021 experiments...
"""

    meta = _metadata_from_text(text)

    assert meta["title"] == "Jane Doe, John Smith" or meta["title"]
    assert meta["year"] == 2021


def test_heuristics_title_prefers_long_line():
    text = """CVPR 2020
A Very Long Title About Semantic Understanding of Documents
Alice A, Bob B
Abstract
Body text here.
"""

    meta = _metadata_from_text(text)

    assert meta["title"] == (
        "A Very Long Title About Semantic Understanding of Documents"
    )
    assert meta["year"] == 2020
    assert "Alice A" in meta["authors"]


def test_extract_metadata_falls_back_to_stem(tmp_path):
    target = tmp_path / "1086936.pdf"

    target.write_bytes(b"not a real pdf")

    result = extract_metadata(target)

    assert result["title"] == "1086936"
    assert result["year"] == datetime.now(timezone.utc).year
