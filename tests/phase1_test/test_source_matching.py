import pytest

from app.pipeline.llm_utils import (
    LLMOutputError,
    find_source_offsets,
)


def test_exact_match_offsets_unchanged():
    chunk = "The treatment improved accuracy by 15%."

    start, end = find_source_offsets(
        source_sentence="The treatment improved accuracy by 15%.",
        chunk_text=chunk,
        chunk_start_offset=100,
    )

    assert (start, end) == (100, 139)


def test_whitespace_and_newline_differences_match():
    chunk = "Alpha results improved in 2021.\n\nThe  method worked well."

    start, end = find_source_offsets(
        source_sentence="The method worked well.",
        chunk_text=chunk,
        chunk_start_offset=0,
    )

    assert (start, end) == (33, 57)


def test_case_differences_match():
    chunk = "Alpha results improved in 2021.\n\nThe  method worked well."

    start, end = find_source_offsets(
        source_sentence="THE METHOD WORKED WELL.",
        chunk_text=chunk,
        chunk_start_offset=500,
    )

    assert (start, end) == (533, 557)


def test_unicode_quote_and_dash_variants_match():
    chunk = "Patients said it \u201cworked\u201d well\u2014quickly."

    start, end = find_source_offsets(
        source_sentence='it "worked" well-quickly.',
        chunk_text=chunk,
        chunk_start_offset=0,
    )

    assert (start, end) == (14, 39)


def test_dropped_trailing_period_matches_fuzzily():
    chunk = "Treatment raised accuracy by 12% overall."

    start, end = find_source_offsets(
        source_sentence="Treatment raised accuracy by 12% overall",
        chunk_text=chunk,
        chunk_start_offset=0,
    )

    assert (start, end) == (0, 40)


def test_inserted_word_still_rejected():
    chunk = "The treatment improved accuracy."

    with pytest.raises(LLMOutputError, match="not found"):
        find_source_offsets(
            source_sentence=(
                "The treatment greatly improved accuracy."
            ),
            chunk_text=chunk,
            chunk_start_offset=0,
        )


def test_paraphrased_word_still_rejected():
    chunk = "The treatment improved accuracy by 15%."

    with pytest.raises(LLMOutputError, match="not found"):
        find_source_offsets(
            source_sentence=(
                "The treatment boosted accuracy by 15%."
            ),
            chunk_text=chunk,
            chunk_start_offset=0,
        )


def test_empty_source_sentence_rejected():
    chunk = "Some text here."

    with pytest.raises(LLMOutputError, match="not found"):
        find_source_offsets(
            source_sentence="   ",
            chunk_text=chunk,
            chunk_start_offset=0,
        )
