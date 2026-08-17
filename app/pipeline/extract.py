from __future__ import annotations

import logging
from collections.abc import Callable

from app.pipeline.llm_utils import (
    LLMOutputError,
    parse_json_array,
    validate_claims,
)
from app.schemas import Claim

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

            parsed = parse_json_array(raw_output)

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
