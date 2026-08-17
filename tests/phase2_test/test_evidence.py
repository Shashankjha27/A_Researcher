from app.retrieval.evidence import retrieve_evidence


def test_retrieve_evidence_returns_top_k():
    claim = "The treatment improved recovery."

    sentences = [
        "The weather was cloudy today.",
        "The treatment improved recovery by 18%.",
        "The hospital opened in 2020.",
    ]

    results = retrieve_evidence(
        claim,
        sentences,
        top_k=2,
    )

    assert len(results) == 2

    for sentence, score in results:
        assert sentence in sentences
        assert isinstance(score, float)