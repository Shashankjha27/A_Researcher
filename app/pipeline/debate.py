"""Adversarial debate mode.

Two LLM roles argue for and against a claim, constrained to the
paper's own evidence sentences; a judge turn renders a verdict from
the transcript.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.schemas import DebateRecord, DebateTurn
from app.scoring.verdict import Verdict

logger = logging.getLogger(__name__)

_VALID_VERDICTS = {verdict.value for verdict in Verdict}

_DEFENDER_PROMPT = """You are the DEFENDER in an adversarial review of a scientific claim.

Claim: {claim}

Evidence sentences from the paper (numbered):
{evidence}

Argue that the claim is SUPPORTED by this evidence. You may ONLY cite
the numbered evidence sentences above — no outside knowledge. Be
specific: reference sentence numbers and quote short fragments.
Maximum 150 words."""

_ATTACKER_PROMPT = """You are the ATTACKER in an adversarial review of a scientific claim.

Claim: {claim}
Defender's argument:
{defender_case}

Evidence sentences from the paper (numbered):
{evidence}

Argue that the claim is NOT adequately supported — point out gaps,
overreach, or missing controls in the evidence. You may ONLY cite the
numbered evidence sentences above — no outside knowledge. Maximum 150
words."""

_JUDGE_PROMPT = """You are the JUDGE in an adversarial debate about a scientific claim.

Claim: {claim}

Evidence sentences from the paper (numbered):
{evidence}

DEFENDER's argument:
{defender_case}

ATTACKER's argument:
{attacker_case}

Weigh both arguments strictly against the evidence. Reply with ONLY a
JSON object, no other text:
{{"verdict": "<one of: supported, provisionally_supported, contradicted, conflicting, insufficient>", "rationale": "<max 80 words>"}}"""


def _format_evidence(evidence_texts: list[str]) -> str:
    return "\n".join(
        f"[{index + 1}] {text}"
        for index, text in enumerate(evidence_texts)
    )


def _parse_judge_output(raw_output: str) -> tuple[Verdict, str]:
    match = re.search(r"\{.*\}", raw_output, re.DOTALL)

    if match:
        try:
            parsed = json.loads(match.group(0))
            verdict = str(parsed.get("verdict", "")).strip()

            if verdict in _VALID_VERDICTS:
                rationale = str(parsed.get("rationale", "")).strip()
                return Verdict(verdict), rationale or "No rationale given."
        except json.JSONDecodeError:
            pass

    logger.warning("judge output not parseable; defaulting to insufficient")

    return Verdict.INSUFFICIENT, (
        "Judge output could not be parsed: "
        f"{raw_output.strip()[:200]}"
    )


def run_debate(
    llm_call: Any,
    claim_id: str,
    paper_id: str,
    claim_text: str,
    evidence_texts: list[str],
    model_label: str,
) -> DebateRecord:
    """Run one defender/attacker/judge round over a claim."""
    if not evidence_texts:
        raise ValueError(
            "No evidence available for this claim; cannot debate."
        )

    evidence_block = _format_evidence(evidence_texts)

    defender_case = llm_call(
        _DEFENDER_PROMPT.format(
            claim=claim_text,
            evidence=evidence_block,
        )
    )

    attacker_case = llm_call(
        _ATTACKER_PROMPT.format(
            claim=claim_text,
            defender_case=defender_case,
            evidence=evidence_block,
        )
    )

    judge_raw = llm_call(
        _JUDGE_PROMPT.format(
            claim=claim_text,
            evidence=evidence_block,
            defender_case=defender_case,
            attacker_case=attacker_case,
        )
    )

    judge_verdict, judge_rationale = _parse_judge_output(judge_raw)

    return DebateRecord(
        debate_id=f"db_{uuid.uuid4().hex[:12]}",
        claim_id=claim_id,
        paper_id=paper_id,
        model=model_label,
        rounds=1,
        turns=[
            DebateTurn(role="defender", text=defender_case.strip()),
            DebateTurn(role="attacker", text=attacker_case.strip()),
            DebateTurn(role="judge", text=judge_rationale),
        ],
        judge_verdict=judge_verdict,
        judge_rationale=judge_rationale,
        created_at=datetime.now(timezone.utc),
    )
