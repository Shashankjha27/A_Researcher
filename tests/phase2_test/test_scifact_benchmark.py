from unittest.mock import patch

from benchmark.scifact import predict_claim

CLAIM = "The drug lowers blood pressure."
EVIDENCE = "Systolic pressure dropped significantly in the treated group."


def _patch_retrieval(sentences: list[tuple[str, float]]):
    return patch(
        "benchmark.scifact.retrieve_evidence",
        return_value=sentences,
    )


def test_classify_uses_evidence_as_premise():
    with _patch_retrieval([(EVIDENCE, 0.9)]), patch(
        "benchmark.scifact.classify",
        return_value=("neutral", 0.5),
    ) as mock_classify:
        predict_claim(CLAIM, [EVIDENCE], threshold=0.7)

    mock_classify.assert_called_once_with(EVIDENCE, CLAIM)


def test_entailment_above_threshold_is_support():
    with _patch_retrieval([(EVIDENCE, 0.9)]), patch(
        "benchmark.scifact.classify",
        return_value=("entailment", 0.88),
    ):
        label, probability, sentence, score = predict_claim(
            CLAIM,
            [EVIDENCE],
            threshold=0.7,
        )

    assert label == "SUPPORT"
    assert probability == 0.88
    assert sentence == EVIDENCE
    assert score == 0.9


def test_contradiction_takes_precedence_over_support():
    sentences = [
        ("Blood pressure was unchanged.", 0.8),
        ("The drug raises blood pressure.", 0.7),
    ]

    def fake_classify(premise, hypothesis):
        if "raises" in premise:
            return "contradiction", 0.81

        return "entailment", 0.75

    with _patch_retrieval(sentences), patch(
        "benchmark.scifact.classify",
        side_effect=fake_classify,
    ):
        label, probability, _, _ = predict_claim(
            CLAIM,
            [text for text, _ in sentences],
            threshold=0.7,
        )

    assert label == "CONTRADICT"
    assert probability == 0.81


def test_below_threshold_returns_not_enough_info():
    with _patch_retrieval([(EVIDENCE, 0.9)]), patch(
        "benchmark.scifact.classify",
        return_value=("entailment", 0.61),
    ):
        label, probability, sentence, _ = predict_claim(
            CLAIM,
            [EVIDENCE],
            threshold=0.7,
        )

    assert label == "NOT_ENOUGH_INFO"
    assert probability == 0.0
    assert sentence is None


def test_no_sentences_returns_not_enough_info():
    label, probability, sentence, score = predict_claim(
        CLAIM,
        [],
        threshold=0.7,
    )

    assert label == "NOT_ENOUGH_INFO"
    assert probability == 0.0
    assert sentence is None
    assert score == 0.0
