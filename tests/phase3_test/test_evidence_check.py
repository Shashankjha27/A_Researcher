import pytest

from app.nli import evidence_check
from app.nli.evidence_check import evidence_support_counts


def test_empty_evidence_returns_zero_counts():
    result = evidence_support_counts(
        claim_text="Some claim.",
        evidence_texts=[],
        threshold=0.60,
    )

    assert result == (0, 0, 0.0)


def test_blank_evidence_sentences_are_skipped(monkeypatch):
    calls = []

    def fake_check_relation(text_a, text_b, threshold):
        calls.append(text_b)
        return "neutral", 0.3

    monkeypatch.setattr(
        evidence_check,
        "check_relation",
        fake_check_relation,
    )

    result = evidence_support_counts(
        claim_text="Some claim.",
        evidence_texts=["   ", "", "Real sentence."],
        threshold=0.60,
    )

    assert result == (0, 0, 0.0)
    assert calls == ["Real sentence."]


def test_support_and_contradiction_are_counted(monkeypatch):
    script = [
        ("support", 0.81),
        ("contradiction", 0.77),
        ("neutral", 0.55),
    ]

    def fake_check_relation(text_a, text_b, threshold):
        return script.pop(0)

    monkeypatch.setattr(
        evidence_check,
        "check_relation",
        fake_check_relation,
    )

    support_count, contradiction_count, max_probability = (
        evidence_support_counts(
            claim_text="Some claim.",
            evidence_texts=["a", "b", "c"],
            threshold=0.60,
        )
    )

    assert (support_count, contradiction_count) == (1, 1)
    assert max_probability == pytest.approx(0.81)


def test_neutral_probability_is_not_firing(monkeypatch):
    def fake_check_relation(text_a, text_b, threshold):
        return "neutral", 0.90

    monkeypatch.setattr(
        evidence_check,
        "check_relation",
        fake_check_relation,
    )

    result = evidence_support_counts(
        claim_text="Some claim.",
        evidence_texts=["a", "b"],
        threshold=0.95,
    )

    assert result == (0, 0, 0.0)
