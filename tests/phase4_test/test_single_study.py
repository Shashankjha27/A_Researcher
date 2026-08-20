from app.flags.single_study import check_single_study


def test_no_claim_text_no_flag():
    assert check_single_study(None) is None


def test_no_consensus_phrase_no_flag():
    result = check_single_study(
        "Drug A reduced symptoms by 40%.",
        support_count=1,
    )

    assert result is None


def test_consensus_with_one_support_flagged():
    result = check_single_study(
        "X has been shown to improve Y.",
        support_count=1,
    )

    assert result is not None
    assert result["flag_type"] == "single_study_as_consensus"
    assert result["severity"] == "medium"
    assert "has been shown" in result["rationale_string"]


def test_consensus_with_multiple_support_no_flag():
    result = check_single_study(
        "X has been shown to improve Y.",
        support_count=2,
    )

    assert result is None


def test_consensus_with_zero_support_flagged():
    result = check_single_study(
        "X has been shown to improve Y.",
        support_count=0,
    )

    assert result is not None
    assert result["flag_type"] == "single_study_as_consensus"
    assert "0 study" in result["rationale_string"]


def test_multiple_phrases_match_uses_first():
    result = check_single_study(
        "X is established and well known.",
        support_count=1,
    )

    assert result is not None
    assert "is established" in result["rationale_string"]
