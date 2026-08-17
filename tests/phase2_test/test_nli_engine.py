from app.nli.nli_engine import classify


def test_classify_returns_label_and_probability():
    label, probability = classify(
        "The treatment improved recovery.",
        "The treatment improved recovery.",
    )

    assert isinstance(label, str)
    assert 0.0 <= probability <= 1.0