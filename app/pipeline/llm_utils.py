from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import Claim, Provenance
from app.schemas.enums import EffectDirection, MethodType

logger = logging.getLogger(__name__)

# A fuzzy provenance match below this ratio is rejected. High enough
# that inserted/paraphrased words (~0.85-0.90 ratio) stay rejected,
# low enough to accept cosmetic diffs like a dropped trailing period.
FUZZY_MATCH_THRESHOLD = 0.93

_FUZZY_WINDOW_DELTAS = (0, -2, 2, -4, 4)

_CHAR_MAP = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00a0": " ",
    }
)


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

    if isinstance(parsed, dict):
        # Small models often wrap the array in an object
        # ({"claims": [...]}) or return a single item object
        # instead of an array. Unwrap one list-valued entry, or
        # lift a lone claim-shaped object into an array; item
        # validation stays strict either way.
        if "claim_text" in parsed:
            parsed = [parsed]
        else:
            list_values = [
                value
                for value in parsed.values()
                if isinstance(value, list)
            ]

            if len(list_values) == 1:
                parsed = list_values[0]

    if not isinstance(parsed, list):
        raise LLMOutputError("expected a JSON array at top level")

    return parsed


def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    """Lowercase, unify lookalike chars, collapse whitespace.

    Returns the normalized string plus a mapping from each normalized
    character index back to its index in the original text.
    """
    out: list[str] = []
    mapping: list[int] = []
    pending_space = False

    for i, ch in enumerate(text):
        ch = ch.translate(_CHAR_MAP)

        if ch.isspace():
            if out:
                pending_space = True
            continue

        if pending_space:
            out.append(" ")
            mapping.append(i)
            pending_space = False

        out.append(ch.lower())
        mapping.append(i)

    return "".join(out), mapping


def _normalize(text: str) -> str:
    return _normalize_with_map(text)[0]


def _exact_span(
    source_sentence: str,
    chunk_text: str,
) -> tuple[int, int] | None:
    start = chunk_text.find(source_sentence)

    if start < 0:
        return None

    return start, start + len(source_sentence)


def _normalized_span(
    source_sentence: str,
    chunk_text: str,
) -> tuple[int, int] | None:
    norm_chunk, chunk_map = _normalize_with_map(chunk_text)
    norm_source, _ = _normalize_with_map(source_sentence)

    if not norm_source:
        return None

    start = norm_chunk.find(norm_source)

    if start < 0:
        return None

    end = start + len(norm_source) - 1

    return chunk_map[start], chunk_map[end] + 1


def _fuzzy_span(
    source_sentence: str,
    chunk_text: str,
) -> tuple[int, int] | None:
    words = [
        (match.group(), match.start())
        for match in re.finditer(r"\S+", chunk_text)
    ]

    n_source = len(source_sentence.split())

    if not words or n_source == 0:
        return None

    norm_source = _normalize(source_sentence)
    best_ratio = 0.0
    best_span: tuple[int, int] | None = None

    for delta in _FUZZY_WINDOW_DELTAS:
        size = n_source + delta

        if size <= 0 or size > len(words):
            continue

        for i in range(len(words) - size + 1):
            window_words = words[i : i + size]
            window = " ".join(word for word, _ in window_words)
            ratio = SequenceMatcher(
                None,
                _normalize(window),
                norm_source,
            ).ratio()

            if ratio > best_ratio:
                last_word, last_start = window_words[-1]
                best_ratio = ratio
                best_span = (window_words[0][1], last_start + len(last_word))

            if best_ratio > 0.995:
                break

    if best_span is None or best_ratio < FUZZY_MATCH_THRESHOLD:
        return None

    logger.info(
        "source_sentence matched fuzzily (ratio %.2f)",
        best_ratio,
    )

    return best_span


def find_source_offsets(
    source_sentence: str,
    chunk_text: str,
    chunk_start_offset: int,
) -> tuple[int, int]:
    span = _exact_span(source_sentence, chunk_text)

    if span is None:
        span = _normalized_span(source_sentence, chunk_text)

    if span is None:
        span = _fuzzy_span(source_sentence, chunk_text)

    if span is None:
        raise LLMOutputError("source_sentence not found verbatim in chunk")

    start, end = span

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
    if isinstance(item, dict) and item.get("effect_direction") is None:
        item = {
            **item,
            "effect_direction": EffectDirection.MIXED.value,
        }

        logger.info(
            "item %d: coerced null effect_direction to 'mixed'",
            index,
        )

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
