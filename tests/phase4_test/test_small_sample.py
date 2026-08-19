from app.flags.small_sample import check_small_sample


def test_small_sample_flagged():
    result = check_small_sample(20)

    assert result is not None
    assert result["flag_type"] == "small_sample"
    assert result["severity"] == "medium"


def test_large_sample_not_flagged():
    result = check_small_sample(100)

    assert result is None


def test_missing_sample_not_flagged():
    result = check_small_sample(None)

    assert result is None