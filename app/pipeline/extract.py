from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable

from app.pipeline.ingest import split_sentences
from app.pipeline.llm_utils import (
    LLMOutputError,
    parse_json_array,
    validate_claims,
)
from app.schemas import Claim

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

MAX_WINDOW_CHARS = int(
    os.environ.get("AR_EXTRACT_MAX_CHARS", "2000")
)

SKIP_SECTIONS = frozenset(
    {
        "references",
        "acknowledgements",
        "acknowledgments",
    }
)

_RESULT_SIGNAL_RE = re.compile(
    r"""
    \bp\s*[<=]\s*\d?\.\d+
    | %\s*[<=>]?
    | [0-9]+(?:\.[0-9]+)?\s?%
    | \b(?:we|our study|this study)\s+(?:found|observe[d]?|show(?:ed)?|demonstrat\w+)
    | \bsignifican(?:t|tly)\b
    | \b(?:improved?|reduced?|increased?|decreased?|outperform\w*)\b
    | \baccuracy\s+of\b
    | \b(?:patients|participants|subjects|samples|users|trials|mice|cells)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_PROMPT = """You are extracting empirical claims from a scientific paper excerpt.

Return ONLY a JSON array. No prose, no markdown fences, no explanation.

Each element must have exactly these fields:
- "claim_text": string, a single self-contained empirical claim
- "method_type": one of "RCT", "observational", "meta-analysis", "other"
- "effect_direction": one of "positive", "negative", "null_effect", "mixed"
- "sample_size": integer or null if not stated
- "source_sentence": the EXACT sentence from the text this claim is drawn from (verbatim, no paraphrasing)

Rules:
- Extract up to 10 claims.
- Only extract claims that state an empirical result (an effect, association, or finding backed by data).
- Skip background statements, citations of other work, and methodology-only sentences with no result.
- Every "source_sentence" must appear word-for-word in the TEXT below.

Example output shape:
[
  {{"claim_text": "...", "method_type": "RCT", "effect_direction": "positive", "sample_size": 200, "source_sentence": "..."}}
]

TEXT:
{chunk_text}

Only return [] if the text above contains no empirical results at all."""


class ExtractionError(Exception):
    pass


def _has_result_signals(text: str) -> bool:
    return bool(_RESULT_SIGNAL_RE.search(text))


def _split_windows(
    chunk_text: str,
    max_chars: int,
) -> list[tuple[str, int]]:
    """Split a chunk into sentence-aligned windows of <= max_chars.

    Returns (window_text, offset_within_chunk) pairs. A single
    sentence longer than max_chars becomes its own window.
    """
    sentences = split_sentences(chunk_text)

    if not sentences:
        return []

    windows: list[tuple[str, int]] = []
    start = sentences[0][1]

    for index, (_, sentence_start, sentence_end) in enumerate(sentences):
        is_last = index == len(sentences) - 1
        next_start = (
            sentences[index + 1][1] if not is_last else None
        )

        if next_start is not None and next_start - start <= max_chars:
            continue

        windows.append(
            (
                chunk_text[start:sentence_end],
                start,
            )
        )

        if not is_last:
            start = next_start

    return windows


def _extract_window(
    llm_call: Callable[[str], str],
    chunk_text: str,
    paper_id: str,
    section: str,
    chunk_start_offset: int,
) -> list[Claim]:
    base_prompt = _PROMPT.format(
        chunk_text=chunk_text
    )

    last_output = ""
    last_error = ""
    had_items = False

    for attempt in range(MAX_RETRIES + 1):
        if attempt == 0:
            prompt = base_prompt
        else:
            prompt = (
                f"{base_prompt}\n\n"
                "Your previous response failed validation.\n"
                f"Validation error:\n{last_error}\n\n"
                f"Previous response:\n{last_output}\n\n"
                "Return ONLY the corrected JSON array."
            )

        raw_output = ""

        try:
            raw_output = llm_call(prompt)

            if not isinstance(raw_output, str):
                raise ExtractionError(
                    "LLM call did not return a string"
                )

            parsed = parse_json_array(raw_output)

            if not parsed and _has_result_signals(chunk_text):
                raise LLMOutputError(
                    "model returned [] but the text contains "
                    "result-like sentences; re-examine the text "
                    "and extract the empirical claims"
                )

            if attempt > 0 and had_items and not parsed:
                raise LLMOutputError(
                    "model returned an empty array on retry after "
                    "previously producing items; refusing to accept "
                    "the empty-array surrender"
                )

            had_items = len(parsed) > 0

            claims = validate_claims(
                parsed=parsed,
                paper_id=paper_id,
                section=section,
                chunk_text=chunk_text,
                chunk_start_offset=chunk_start_offset,
            )

            logger.info(
                "extracted %d claims from %s sec=%s offset=%d",
                len(claims),
                paper_id,
                section,
                chunk_start_offset,
            )

            return claims

        except (LLMOutputError, ExtractionError) as exc:
            last_error = str(exc)
            last_output = raw_output

            logger.warning(
                "extraction attempt %d/%d failed for "
                "%s sec=%s offset=%d: %s | raw output prefix: %.200r",
                attempt + 1,
                MAX_RETRIES + 1,
                paper_id,
                section,
                chunk_start_offset,
                last_error,
                raw_output,
            )

        except Exception as exc:
            last_error = f"LLM call failed: {exc}"
            last_output = ""

            logger.exception(
                "unexpected extraction failure for "
                "%s sec=%s offset=%d",
                paper_id,
                section,
                chunk_start_offset,
            )

    logger.warning(
        "extraction failed after %d attempts; "
        "discarding chunk %s sec=%s offset=%d",
        MAX_RETRIES + 1,
        paper_id,
        section,
        chunk_start_offset,
    )

    return []


def extract_claims_from_chunk(
    llm_call: Callable[[str], str],
    chunk_text: str,
    paper_id: str,
    section: str,
    chunk_start_offset: int,
) -> list[Claim]:
    """
    Extract empirical claims from one paper chunk.

    The LLM performs claim extraction only.
    All structural, enum, provenance, and Pydantic validation
    happens locally.

    Chunks longer than MAX_WINDOW_CHARS are split into
    sentence-aligned windows; each window is extracted separately
    with its absolute offsets preserved.
    """
    if not chunk_text.strip():
        return []

    if section.lower() in SKIP_SECTIONS:
        logger.info(
            "skipping LLM extraction for %s sec=%s",
            paper_id,
            section,
        )
        return []

    claims: list[Claim] = []

    for window_text, window_offset in _split_windows(
        chunk_text,
        MAX_WINDOW_CHARS,
    ):
        claims.extend(
            _extract_window(
                llm_call=llm_call,
                chunk_text=window_text,
                paper_id=paper_id,
                section=section,
                chunk_start_offset=(
                    chunk_start_offset + window_offset
                ),
            )
        )

    return claims
