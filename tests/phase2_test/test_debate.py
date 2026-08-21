import json

import pytest

from app.pipeline.debate import _parse_judge_output, run_debate
from app.scoring.verdict import Verdict


def test_parse_judge_output_valid():
    verdict, rationale = _parse_judge_output(
    'Here is my ruling: {"verdict": "supported", "rationale": "Evidence [1] states it directly."}'
    )

    assert verdict is Verdict.SUPPORTED
    assert "Evidence [1]" in rationale


def test_parse_judge_output_invalid_defaults_insufficient():
    verdict, rationale = _parse_judge_output("I cannot decide.")

    assert verdict is Verdict.INSUFFICIENT
    assert "could not be parsed" in rationale


def test_parse_judge_output_rejects_unknown_verdict():
    verdict, _ = _parse_judge_output(
        '{"verdict": "totally_false", "rationale": "nope"}'
    )

    assert verdict is Verdict.INSUFFICIENT


def _fake_llm(responses: list[str]):
    calls = {"count": 0}

    def call(prompt: str) -> str:
        index = min(calls["count"], len(responses) - 1)
        calls["count"] += 1
        return responses[index]

    return call, calls


def test_run_debate_builds_transcript_and_judges():
    judge_json = json.dumps(
        {
            "verdict": "provisionally_supported",
            "rationale": "Single study, but consistent.",
        }
    )
    llm_call, calls = _fake_llm(
        [
            "The claim holds: [1] shows the effect.",
            "[1] is a single small study; controls are unclear.",
            judge_json,
        ]
    )

    record = run_debate(
        llm_call=llm_call,
        claim_id="c_0001",
        paper_id="p_0001",
        claim_text="X improves Y",
        evidence_texts=["X improved Y.", "The study had 40 subjects."],
        model_label="gemini/test",
    )

    assert calls["count"] == 3
    assert record.claim_id == "c_0001"
    assert record.model == "gemini/test"
    assert [turn.role for turn in record.turns] == [
        "defender",
        "attacker",
        "judge",
    ]
    assert record.judge_verdict is Verdict.PROVISIONALLY_SUPPORTED
    assert record.debate_id.startswith("db_")

    defender_prompt_evidence = "[1] X improved Y."
    assert defender_prompt_evidence


def test_run_debate_requires_evidence():
    llm_call, _ = _fake_llm(["a", "b", '{"verdict": "supported"}'])

    with pytest.raises(ValueError):
        run_debate(
            llm_call=llm_call,
            claim_id="c_0001",
            paper_id="p_0001",
            claim_text="X improves Y",
            evidence_texts=[],
            model_label="test",
        )
