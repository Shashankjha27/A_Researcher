from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.schemas import Claim, Provenance
from app.schemas.enums import EffectDirection, MethodType

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

_PROMPT = """You are extracting empirical claims from a scientific paper excerpt.

Return ONLY a JSON array. No prose, no markdown fences, no explanation.

Each element must have exactly these fields:
- "claim_text": string, a single self-contained empirical claim
- "method_type": one of "RCT", "observational", "meta-analysis", "other"
- "effect_direction": one of "positive", "negative", "null_effect", "mixed"
- "sample_size": integer or null if not stated
- "source_sentence": the EXACT sentence from the text this claim is drawn from (verbatim, no paraphrasing)

Only extract claims that state an empirical result (an effect, association, or finding backed by data).
Skip background statements, citations of other work, and methodology-only sentences with no result.

Return [] if there are no empirical claims in this text.

TEXT:
{chunk_text}
"""


class ExtractionError(Exception):
    pass


def _strip_fences(text: str) -> str:
    text = text.strip()

    if not text.startswith("```"):
        return text

    lines = text.splitlines()

    if lines and lines[0].strip().lower() in {"```", "```json"}:
        lines = lines[1:]

    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def _find_source_offsets(
    source_sentence: str,
    chunk_text: str,
    chunk_start_offset: int,
) -> tuple[int, int]:
    start = chunk_text.find(source_sentence)

    if start == -1:
        raise ExtractionError(
            "source_sentence not found verbatim in chunk"
        )

    end = start + len(source_sentence)

    return (
        chunk_start_offset + start,
        chunk_start_offset + end,
    )


def _to_claim(
    item: Any,
    index: int,
    paper_id: str,
    section: str,
    chunk_start_offset: int,
    chunk_text: str,
) -> Claim:
    if not isinstance(item, dict):
        raise ExtractionError(
            f"item {index} is not an object"
        )

    claim_text = item.get("claim_text")
    method_value = item.get("method_type")
    effect_value = item.get("effect_direction")
    sample_size = item.get("sample_size")
    source_sentence = item.get("source_sentence")

    if not isinstance(claim_text, str) or not claim_text.strip():
        raise ExtractionError(
            f"item {index}: claim_text missing or empty"
        )

    if not isinstance(source_sentence, str) or not source_sentence.strip():
        raise ExtractionError(
            f"item {index}: source_sentence missing or empty"
        )

    if (
        sample_size is not None
        and (
            not isinstance(sample_size, int)
            or isinstance(sample_size, bool)
        )
    ):
        raise ExtractionError(
            f"item {index}: sample_size must be an integer or null"
        )

    if isinstance(sample_size, int) and sample_size < 0:
        raise ExtractionError(
            f"item {index}: sample_size cannot be negative"
        )

    try:
        method_type = MethodType(method_value)
    except (TypeError, ValueError) as exc:
        raise ExtractionError(
            f"item {index}: invalid method_type: {method_value!r}"
        ) from exc

    try:
        effect_direction = EffectDirection(effect_value)
    except (TypeError, ValueError) as exc:
        raise ExtractionError(
            f"item {index}: invalid effect_direction: {effect_value!r}"
        ) from exc

    start_offset, end_offset = _find_source_offsets(
        source_sentence=source_sentence,
        chunk_text=chunk_text,
        chunk_start_offset=chunk_start_offset,
    )

    try:
        return Claim(
            claim_id=(
                f"cl_{paper_id}_{section}_"
                f"{chunk_start_offset}_{index}"
            ),
            paper_id=paper_id,
            claim_text=claim_text.strip(),
            method_type=method_type,
            effect_direction=effect_direction,
            provenance=Provenance(
                source_sentence=source_sentence,
                start_offset=start_offset,
                end_offset=end_offset,
            ),
            sample_size=sample_size,
        )
    except ValidationError as exc:
        raise ExtractionError(
            f"item {index}: schema validation failed: {exc}"
        ) from exc


def _parse_and_validate(
    raw_output: str,
    paper_id: str,
    section: str,
    chunk_start_offset: int,
    chunk_text: str,
) -> list[Claim]:
    text = _strip_fences(raw_output)

    if not text:
        raise ExtractionError("empty LLM response")

    try:
        parsed: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExtractionError(
            f"invalid JSON: {exc.msg} at position {exc.pos}"
        ) from exc

    if not isinstance(parsed, list):
        raise ExtractionError(
            "expected a JSON array at top level"
        )

    claims: list[Claim] = []

    for index, item in enumerate(parsed):
        claims.append(
            _to_claim(
                item=item,
                index=index,
                paper_id=paper_id,
                section=section,
                chunk_start_offset=chunk_start_offset,
                chunk_text=chunk_text,
            )
        )

    return claims


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
    """
    if not chunk_text.strip():
        return []

    base_prompt = _PROMPT.format(
        chunk_text=chunk_text
    )

    last_output = ""
    last_error = ""

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

        try:
            raw_output = llm_call(prompt)

            if not isinstance(raw_output, str):
                raise ExtractionError(
                    "LLM call did not return a string"
                )

            claims = _parse_and_validate(
                raw_output=raw_output,
                paper_id=paper_id,
                section=section,
                chunk_start_offset=chunk_start_offset,
                chunk_text=chunk_text,
            )

            logger.info(
                "extracted %d claims from %s sec=%s offset=%d",
                len(claims),
                paper_id,
                section,
                chunk_start_offset,
            )

            return claims

        except (ExtractionError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            last_output = (
                raw_output
                if "raw_output" in locals()
                else ""
            )

            logger.warning(
                "extraction attempt %d/%d failed for "
                "%s sec=%s offset=%d: %s",
                attempt + 1,
                MAX_RETRIES + 1,
                paper_id,
                section,
                chunk_start_offset,
                last_error,
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

    logger.error(
        "extraction failed after %d attempts; "
        "discarding chunk %s sec=%s offset=%d",
        MAX_RETRIES + 1,
        paper_id,
        section,
        chunk_start_offset,
    )

    return []