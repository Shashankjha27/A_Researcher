from app.pipeline.claimify import (
    build_claimify_candidates,
    build_claimify_context,
    decompose_sentences,
    disambiguate_sentences,
    select_candidate_sentences,
    split_claim_sentences,
)


def test_split_claim_sentences():
    text = (
        "The treatment improved recovery by 18%. "
        "The control group showed no improvement."
    )

    result = split_claim_sentences(text)

    assert len(result) == 2
    assert result[0][0] == "The treatment improved recovery by 18%."
    assert result[1][0] == "The control group showed no improvement."


def test_split_claim_sentences_preserves_offsets():
    text = (
        "The treatment improved recovery by 18%. "
        "The control group showed no improvement."
    )

    result = split_claim_sentences(text)

    for sentence, start, end in result:
        assert text[start:end] == sentence


def test_select_candidate_sentences():
    sentences = [
        ("The treatment improved recovery by 18%.", 0, 39),
        ("The study used a randomized design.", 40, 76),
        ("The protocol was approved by the committee.", 77, 120),
    ]

    result = select_candidate_sentences(sentences)

    assert len(result) == 1
    assert result[0][0] == (
        "The treatment improved recovery by 18%."
    )


def test_select_candidate_sentences_detects_statistics():
    sentences = [
        ("The model achieved 94.2% accuracy.", 0, 34),
        ("The dataset contains several images.", 35, 72),
        ("The result was significant with p < 0.01.", 73, 116),
    ]

    result = select_candidate_sentences(sentences)

    assert len(result) == 2
    assert result[0][0] == (
        "The model achieved 94.2% accuracy."
    )
    assert result[1][0] == (
        "The result was significant with p < 0.01."
    )


def test_select_returns_empty_for_non_empirical_sentences():
    sentences = [
        ("The study was conducted at a university.", 0, 40),
        ("Participants signed informed consent forms.", 41, 82),
    ]

    result = select_candidate_sentences(sentences)

    assert result == []


def test_disambiguate_preserves_selected_claims():
    sentences = [
        (
            "The treatment improved recovery by 18%.",
            0,
            39,
        )
    ]

    result = disambiguate_sentences(sentences)

    assert len(result) == 1
    assert result[0][0] == (
        "The treatment improved recovery by 18%."
    )
    assert result[0][1] == 0
    assert result[0][2] == 39


def test_disambiguate_removes_citation_markers():
    sentences = [
        (
            "The treatment improved recovery by 18% [12].",
            0,
            47,
        )
    ]

    result = disambiguate_sentences(sentences)

    assert len(result) == 1
    assert result[0][0] == (
        "The treatment improved recovery by 18%."
    )


def test_decompose_single_claim():
    sentence = "The treatment improved recovery by 18%."

    result = decompose_sentences(
        [(sentence, 0, len(sentence))]
    )

    assert len(result) == 1
    assert result[0][0] == sentence


def test_decompose_multiple_claims_preserves_subject():
    sentence = (
        "The treatment improved recovery by 18% "
        "and reduced hospital stay by 3 days."
    )

    result = decompose_sentences(
        [(sentence, 0, len(sentence))]
    )

    assert len(result) == 2

    assert result[0][0] == (
        "The treatment improved recovery by 18%."
    )

    assert result[1][0] == (
        "The treatment reduced hospital stay by 3 days."
    )


def test_decompose_preserves_original_source_offsets():
    sentence = (
        "The treatment improved recovery by 18% "
        "and reduced hospital stay by 3 days."
    )

    result = decompose_sentences(
        [(sentence, 100, 100 + len(sentence))]
    )

    assert len(result) == 2

    for _, start, end in result:
        assert start == 100
        assert end == 100 + len(sentence)


def test_decompose_handles_multiple_connectors():
    sentence = (
        "The treatment improved recovery by 18% "
        "and reduced hospital stay by 3 days "
        "while lowering readmission rates by 10%."
    )

    result = decompose_sentences(
        [(sentence, 0, len(sentence))]
    )

    assert len(result) == 3

    assert result[0][0] == (
        "The treatment improved recovery by 18%."
    )
    assert result[1][0] == (
        "The treatment reduced hospital stay by 3 days."
    )
    assert result[2][0] == (
        "The treatment lowering readmission rates by 10%."
    ) or result[2][0] == (
        "lowering readmission rates by 10%."
    )


def test_build_claimify_candidates_runs_all_stages():
    chunk = (
        "The treatment improved recovery by 18% and "
        "reduced hospital stay by 3 days. "
        "The protocol was approved by the committee."
    )

    result = build_claimify_candidates(chunk)

    texts = [sentence for sentence, _, _ in result]

    assert (
        "The treatment improved recovery by 18%."
        in texts
    )

    assert (
        "The treatment reduced hospital stay by 3 days."
        in texts
    )

    assert not any(
        "protocol was approved" in text.lower()
        for text in texts
    )


def test_build_claimify_context():
    chunk = (
        "The treatment improved recovery by 18%. "
        "The protocol was approved by the committee. "
        "The treatment reduced hospital stay by 3 days."
    )

    result = build_claimify_context(chunk)

    assert (
        "The treatment improved recovery by 18%."
        in result
    )

    assert (
        "The treatment reduced hospital stay by 3 days."
        in result
    )

    assert (
        "The protocol was approved by the committee."
        not in result
    )


def test_build_claimify_context_empty():
    chunk = (
        "This section describes the study protocol. "
        "Participants signed consent forms."
    )

    result = build_claimify_context(chunk)

    assert result == ""