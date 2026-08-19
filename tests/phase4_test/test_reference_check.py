from app.flags.reference_check import check_reference


def test_valid_reference_not_flagged():
    result = check_reference(
        "doi:10.1000/example1",
        {"doi:10.1000/example1"},
    )

    assert result is None


def test_unknown_reference_flagged():
    result = check_reference(
        "doi:10.1000/unknown",
        {"doi:10.1000/example1"},
    )

    assert result is not None
    assert result["flag_type"] == "reference_check"
    assert result["severity"] == "high"


def test_missing_reference_flagged():
    result = check_reference(
        None,
        {"doi:10.1000/example1"},
    )

    assert result is not None
    assert result["flag_type"] == "reference_check"


def test_retracted_reference_flagged():
    result = check_reference(
        "doi:10.1000/retracted",
        {"doi:10.1000/retracted"},
        {"doi:10.1000/retracted"},
    )

    assert result is not None
    assert result["flag_type"] == "retracted"
    assert result["severity"] == "high"