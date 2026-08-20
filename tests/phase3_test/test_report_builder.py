from app.scoring.report_builder import build_report


def test_build_report():
    claims = [
        {
            "claim_text": "The treatment improves recovery.",
            "sub_topic": "Treatment effectiveness",
            "confidence_score": 0.89,
            "confidence_components": {
                "nli_confidence": 0.90,
                "evidence_strength": 0.80,
                "agreement": 1.00,
            },
            "verdict": "supported",
            "supporting_evidence": [
                {
                    "paper_id": "paper-1",
                    "text": "Recovery improved after treatment.",
                    "score": 0.91,
                }
            ],
            "contradicting_evidence": [],
            "flags": [],
        }
    ]

    report = build_report(claims)

    assert "# Research Report" in report
    assert "## Treatment effectiveness" in report
    assert "The treatment improves recovery." in report
    assert "**Verdict:** SUPPORTED" in report
    assert "**Confidence:** 0.8900" in report
    assert "Nli Confidence" in report
    assert "Recovery improved after treatment." in report
    assert "**Flags**" in report


def test_build_report_empty_claims():
    report = build_report([])

    assert "# Research Report" in report
    assert "##" not in report or report.count("##") == 0


def test_build_report_custom_title():
    claims = [
        {
            "claim_text": "Test claim.",
            "confidence_score": 0.5,
            "confidence_components": {},
            "verdict": "insufficient",
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "flags": [],
        }
    ]

    report = build_report(claims, title="My Custom Title")

    assert "# My Custom Title" in report


def test_build_report_with_flags():
    claims = [
        {
            "claim_text": "Weak claim.",
            "confidence_score": 0.20,
            "confidence_components": {},
            "verdict": "insufficient",
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "flags": [
                {
                    "flag_type": "small_sample",
                    "severity": "medium",
                    "rationale_string": "Sample too small.",
                }
            ],
        }
    ]

    report = build_report(claims)

    assert "small_sample" in report
    assert "medium" in report
    assert "Sample too small." in report