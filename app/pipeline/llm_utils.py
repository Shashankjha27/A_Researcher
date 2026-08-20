from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import Claim, Provenance
from app.schemas.enums import EffectDirection, MethodType


class LLMOutputError(Exception):
    pass


class _LLMClaimOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_text: str
    method_type: MethodType
    effect_direction: EffectDirection
    sample_size: int | None = Field(default=None, ge=0)
    source_sentence: str


def strip_json_fences(raw_output: str) -> str:
    text = raw_output.strip()

    if not text:
        raise LLMOutputError("empty LLM response")

    if not text.startswith("```"):
        return text

    lines = text.splitlines()

    if lines and lines[0].strip().lower() in {"```", "```json"}:
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines.pop()

    text = "\n".join(lines).strip()

    if not text:
        raise LLMOutputError("empty response after removing markdown fences")
    return text


def parse_json_array(raw_output: str) -> list[Any]:
    text = strip_json_fences(raw_output)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMOutputError(f"invalid JSON: {exc.msg} at position {exc.pos}") from exc

    if not isinstance(parsed, list):
        raise LLMOutputError("expected a JSON array at top level")

    return parsed


def find_source_offsets(
    source_sentence: str,
    chunk_text: str,
    chunk_start_offset: int,
) -> tuple[int, int]:
    start = chunk_text.find(source_sentence)

    if start < 0:
        raise LLMOutputError("source_sentence not found verbatim in chunk")

    end = start + len(source_sentence)

    return (
        chunk_start_offset + start,
        chunk_start_offset + end,
    )


def validate_claim_item(
    item: Any,
    index: int,
    paper_id: str,
    section: str,
    chunk_text: str,
    chunk_start_offset: int,
) -> Claim:
    try:
        base = _LLMClaimOutput.model_validate(item)
    except Exception as exc:
        raise LLMOutputError(f"item {index}: validation failed: {exc}") from exc

    try:
        start_offset, end_offset = find_source_offsets(
            source_sentence=base.source_sentence,
            chunk_text=chunk_text,
            chunk_start_offset=chunk_start_offset,
        )
    except LLMOutputError as exc:
        raise LLMOutputError(f"item {index}: {exc}") from exc

    return Claim.model_construct(
        claim_id=f"cl_{paper_id}_{section}_{chunk_start_offset}_{index}",
        paper_id=paper_id,
        claim_text=base.claim_text.strip(),
        method_type=base.method_type,
        effect_direction=base.effect_direction,
        provenance=Provenance(
            source_sentence=base.source_sentence,
            start_offset=start_offset,
            end_offset=end_offset,
        ),
        sample_size=base.sample_size,
    )


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
            validate_claim_item(
                item=item,
                index=index,
                paper_id=paper_id,
                section=section,
                chunk_text=chunk_text,
                chunk_start_offset=chunk_start_offset,
            )
        )

    return claims
