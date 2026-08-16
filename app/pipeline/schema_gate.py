from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.schemas import Claim, Provenance
from app.schemas.enums import EffectDirection, MethodType


class SchemaGateError(Exception):
    pass

_REQUIRED_FIELDS = frozenset(
    {
        "claim_text",
        "method_type",
        "effect_direction",
        "sample_size",
        "source_sentence",
    }
)
def strip_json_fences(raw_output: str) -> str:
    text = raw_output.strip()

    if not text:
        raise SchemaGateError("empty LLM response")

    if not text.startswith("```"):
        return text

    lines = text.splitlines()

    if lines and lines[0].strip().lower() in {"```","```json"}:
        lines= lines[1:]
    if lines and lines[-1].strip() == "```":
        lines.pop()
    text = "\n".join(lines).strip()

    if not text:
        raise SchemaGateError(
            "empty response after removing markdown fences"
        )
    return text

def parse_json_array(raw_output: str) -> list[Any]:
    text =  strip_json_fences(raw_output)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemaGateError(
            f"invalid JSON: {exc.msg} at position {exc.pos}"
        ) from exc

    if not isinstance(parsed , list):
        raise SchemaGateError(
            "expected a JSON array at top level"
        )
    return parsed

def _source_offsets(
    source_sentence: str,
    chunk_text: str,
    chunk_start_offset: int,
) -> tuple[int, int]:
    start = chunk_text.find(source_sentence)

    if start < 0:
        raise SchemaGateError(
            "source_sentence not found verbatim in chunk"
        )

    end = start + len(source_sentence)

    return (
        chunk_start_offset + start,
        chunk_start_offset + end,
    )
    
def _validate_sample_size(
    sample_size: Any,
    index: int,
) -> None:
    if sample_size is None:
        return

    if isinstance(sample_size, bool) or not isinstance(sample_size, int):
        raise SchemaGateError(
            f"item {index}: sample_size must be an integer or null"
        )

    if sample_size < 0:
        raise SchemaGateError(
            f"item {index}: sample_size cannot be negative"
        )

def _validate_item(
    item: Any,
    index: int,
    paper_id: str,
    section: str,
    chunk_text: str,
    chunk_start_offset: int,
) -> Claim:
    if not isinstance(item, dict):
        raise SchemaGateError(
            f"item {index}: expected an object"
        )

    missing = _REQUIRED_FIELDS - item.keys()

    if missing:
        raise SchemaGateError(
            f"item {index}: missing required fields: "
            f"{', '.join(sorted(missing))}"
        )

    extra = item.keys() - _REQUIRED_FIELDS

    if extra:
        raise SchemaGateError(
            f"item {index}: unexpected fields: "
            f"{', '.join(sorted(extra))}"
        )

    claim_text = item["claim_text"]
    method_value = item["method_type"]
    effect_value = item["effect_direction"]
    sample_size = item["sample_size"]
    source_sentence = item["source_sentence"]

    if not isinstance(claim_text, str) or not claim_text.strip():
        raise SchemaGateError(
            f"item {index}: claim_text must be a non-empty string"
        )

    if (
        not isinstance(source_sentence, str)
        or not source_sentence.strip()
    ):
        raise SchemaGateError(
            f"item {index}: source_sentence must be a non-empty string"
        )

    _validate_sample_size(sample_size, index)

    try:
        method_type = MethodType(method_value)
    except (TypeError, ValueError) as exc:
        raise SchemaGateError(
            f"item {index}: invalid method_type: {method_value!r}"
        ) from exc

    try:
        effect_direction = EffectDirection(effect_value)
    except (TypeError, ValueError) as exc:
        raise SchemaGateError(
            f"item {index}: invalid effect_direction: {effect_value!r}"
        ) from exc

    start_offset, end_offset = _source_offsets(
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
        raise SchemaGateError(
            f"item {index}: schema validation failed: {exc}"
        ) from exc


def validate_claims(
    parsed: list[Any],
    paper_id: str,
    section: str,
    chunk_text: str,
    chunk_start_offset: int,
) -> list[Claim]:
    claims: list[Claim] = []

    for index, item in enumerate(parsed):
        claims.append(
            _validate_item(
                item=item,
                index=index,
                paper_id=paper_id,
                section=section,
                chunk_text=chunk_text,
                chunk_start_offset=chunk_start_offset,
            )
        )

    return claims


def validate_llm_output(
    raw_output: str,
    paper_id: str,
    section: str,
    chunk_text: str,
    chunk_start_offset: int,
) -> list[Claim]:
    parsed = parse_json_array(raw_output)

    return validate_claims(
        parsed=parsed,
        paper_id=paper_id,
        section=section,
        chunk_text=chunk_text,
        chunk_start_offset=chunk_start_offset,
    )