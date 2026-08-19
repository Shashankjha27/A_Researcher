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