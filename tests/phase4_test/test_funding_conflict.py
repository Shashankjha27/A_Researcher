from app.flags.funding_conflict import check_funding_conflict


def test_no_funding_no_flag():
    assert check_funding_conflict(None) is None


def test_empty_funding_no_flag():
    assert check_funding_conflict("   ") is None


def test_pharma_funding_flagged():
    result = check_funding_conflict(
        "Pfizer Pharmaceutical",
        effect_direction="positive",
    )

    assert result is not None
    assert result["flag_type"] == "funding_conflict"
    assert result["severity"] == "medium"
    assert "pharma" in result["rationale_string"].lower()


def test_academic_funding_low_severity():
    result = check_funding_conflict(
        "National Institute of Health",
        effect_direction="negative",
    )

    assert result is not None
    assert result["flag_type"] == "funding_conflict"
    assert result["severity"] == "low"
    assert "no industry-related keywords" in result["rationale_string"].lower()


def test_custom_keywords():
    result = check_funding_conflict(
        "Acme Corp",
        effect_direction="positive",
        keywords=["acme"],
    )

    assert result is not None
    assert result["severity"] == "medium"
    assert "acme" in result["rationale_string"].lower()
