from __future__ import annotations

from typing import Any

from app.pipeline.llm_utils import (
    LLMOutputError,
)
from app.pipeline.llm_utils import (
    parse_json_array as _parse_json_array,
)
from app.pipeline.llm_utils import (
    strip_json_fences as _strip_json_fences,
)
from app.pipeline.llm_utils import (
    validate_claims as _validate_claims,
)
from app.schemas import Claim


class SchemaGateError(Exception):
    pass


def strip_json_fences(raw_output: str) -> str:
    try:
        return _strip_json_fences(raw_output)
    except LLMOutputError as exc:
        raise SchemaGateError(str(exc)) from exc


def parse_json_array(raw_output: str) -> list[Any]:
    try:
        return _parse_json_array(raw_output)
    except LLMOutputError as exc:
        raise SchemaGateError(str(exc)) from exc


def validate_llm_output(
    raw_output: str,
    paper_id: str,
    section: str,
    chunk_text: str,
    chunk_start_offset: int,
) -> list[Claim]:
    try:
        parsed = _parse_json_array(raw_output)
        return _validate_claims(
            parsed=parsed,
            paper_id=paper_id,
            section=section,
            chunk_text=chunk_text,
            chunk_start_offset=chunk_start_offset,
        )
    except LLMOutputError as exc:
        raise SchemaGateError(str(exc)) from exc
