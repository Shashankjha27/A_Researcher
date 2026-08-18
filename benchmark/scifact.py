from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.nli.nli_engine import classify
from app.retrieval.evidence import retrieve_evidence
from config import NLI_THRESHOLD

DATA_DIR = Path("data/scifact")
TOP_K = 5

LABELS = [
    "SUPPORT",
    "CONTRADICT",
    "NEUTRAL",
    "NOT_ENOUGH_INFO",
]


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_corpus(path: Path) -> dict:
    corpus = {}

    for record in load_jsonl(path):
        corpus[record["doc_id"]] = record

    return corpus


def gold_label(record: dict) -> str:
    """
    Convert SciFact evidence annotations into the benchmark label.

    No annotated evidence -> NOT_ENOUGH_INFO.

    Annotated CONTRADICT evidence -> CONTRADICT.

    Otherwise -> SUPPORT.
    """
    evidence = record.get("evidence", {})

    if not evidence:
        return "NOT_ENOUGH_INFO"

    for doc_evidence in evidence.values():
        for item in doc_evidence:
            if item.get("label", "").upper() == "CONTRADICT":
                return "CONTRADICT"

    return "SUPPORT"


def get_candidate_sentences(
    record: dict,
    corpus: dict,
) -> list[str]:
    """
    Collect sentences from the documents cited by the SciFact claim.
    """
    sentences = []

    for doc_id in record.get("cited_doc_ids", []):
        doc = corpus.get(doc_id)

        if not doc:
            continue

        sentences.extend(doc.get("abstract", []))

    return sentences


def predict_claim(
    claim: str,
    sentences: list[str],
    threshold: float,
) -> tuple[str, float, str | None, float]:
    """
    Retrieve top-k evidence using Contriever and classify each
    retrieved sentence with the NLI model.

    Returns:
        label,
        NLI probability,
        selected sentence,
        retrieval score
    """

    if not sentences:
        return "NOT_ENOUGH_INFO", 0.0, None, 0.0

    retrieved = retrieve_evidence(
        claim,
        sentences,
        top_k=TOP_K,
    )

    best_contradiction = None
    best_support = None

    for sentence, retrieval_score in retrieved:
        label, probability = classify(
            claim,
            sentence,
        )

        label = label.lower()

        if (
            label == "contradiction"
            and probability >= threshold
        ):
            candidate = (
                probability,
                sentence,
                retrieval_score,
            )

            if (
                best_contradiction is None
                or probability > best_contradiction[0]
            ):
                best_contradiction = candidate

        elif (
            label == "entailment"
            and probability >= threshold
        ):
            candidate = (
                probability,
                sentence,
                retrieval_score,
            )

            if (
                best_support is None
                or probability > best_support[0]
            ):
                best_support = candidate

    if best_contradiction is not None:
        probability, sentence, retrieval_score = best_contradiction

        return (
            "CONTRADICT",
            probability,
            sentence,
            retrieval_score,
        )

    if best_support is not None:
        probability, sentence, retrieval_score = best_support

        return (
            "SUPPORT",
            probability,
            sentence,
            retrieval_score,
        )

    return "NEUTRAL", 0.0, None, 0.0


def calculate_metrics(
    gold: list[str],
    predicted: list[str],
):
    """
    Calculate per-label precision, recall and F1,
    followed by macro averages.
    """

    rows = []

    for label in LABELS:
        tp = sum(
            g == label and p == label
            for g, p in zip(gold, predicted)
        )

        fp = sum(
            g != label and p == label
            for g, p in zip(gold, predicted)
        )

        fn = sum(
            g == label and p != label
            for g, p in zip(gold, predicted)
        )

        precision = (
            tp / (tp + fp)
            if tp + fp
            else 0.0
        )

        recall = (
            tp / (tp + fn)
            if tp + fn
            else 0.0
        )

        f1 = (
            2 * precision * recall
            / (precision + recall)
            if precision + recall
            else 0.0
        )

        rows.append(
            (
                label,
                precision,
                recall,
                f1,
            )
        )

    macro_precision = (
        sum(row[1] for row in rows)
        / len(rows)
    )

    macro_recall = (
        sum(row[2] for row in rows)
        / len(rows)
    )

    macro_f1 = (
        sum(row[3] for row in rows)
        / len(rows)
    )

    return (
        rows,
        macro_precision,
        macro_recall,
        macro_f1,
    )


def prepare_dataset(split: str):
    """
    Load SciFact claims and corpus and prepare
    candidate evidence sentences.
    """

    claims_path = DATA_DIR / f"claims_{split}.jsonl"
    corpus_path = DATA_DIR / "corpus.jsonl"

    if not claims_path.exists():
        raise FileNotFoundError(
            f"Missing SciFact split: {claims_path}"
        )

    if not corpus_path.exists():
        raise FileNotFoundError(
            f"Missing SciFact corpus: {corpus_path}"
        )

    claims = load_jsonl(claims_path)
    corpus = load_corpus(corpus_path)

    dataset = []

    for record in claims:
        dataset.append(
            {
                "claim": record["claim"],
                "gold": gold_label(record),
                "sentences": get_candidate_sentences(
                    record,
                    corpus,
                ),
            }
        )

    return dataset


def evaluate(
    dataset: list[dict],
    threshold: float,
    show_progress: bool = True,
):
    """
    Run retrieval + NLI over the dataset.
    """

    gold = []
    predicted = []

    total = len(dataset)

    for index, record in enumerate(
        dataset,
        start=1,
    ):
        prediction, _, _, _ = predict_claim(
            record["claim"],
            record["sentences"],
            threshold,
        )

        gold.append(record["gold"])
        predicted.append(prediction)

        if show_progress and (
            index % 10 == 0 or index == total
        ):
            print(
                f"Processed {index}/{total} claims",
                flush=True,
            )

    return calculate_metrics(
        gold,
        predicted,
    )


def print_metrics(
    split: str,
    threshold: float,
    rows,
    precision: float,
    recall: float,
    f1: float,
):
    print()
    print("# SciFact Benchmark")
    print()
    print(f"Split: {split}")
    print(f"Claims: {sum(1 for _ in rows) if False else ''}")
    print(f"Threshold: {threshold:.2f}")
    print(f"Top-k retrieval: {TOP_K}")
    print()

    print(
        f"{'Label':<20}"
        f"{'Precision':>12}"
        f"{'Recall':>12}"
        f"{'F1':>12}"
    )

    print("-" * 56)

    for label, p, r, score in rows:
        print(
            f"{label:<20}"
            f"{p:>12.4f}"
            f"{r:>12.4f}"
            f"{score:>12.4f}"
        )

    print("-" * 56)

    print(
        f"{'MACRO':<20}"
        f"{precision:>12.4f}"
        f"{recall:>12.4f}"
        f"{f1:>12.4f}"
    )


def run(
    split: str,
    threshold: float,
):
    dataset = prepare_dataset(split)

    rows, precision, recall, f1 = evaluate(
        dataset,
        threshold,
    )

    print()
    print("# SciFact Benchmark")
    print()
    print(f"Split: {split}")
    print(f"Claims: {len(dataset)}")
    print(f"Threshold: {threshold:.2f}")
    print(f"Top-k retrieval: {TOP_K}")
    print()

    print(
        f"{'Label':<20}"
        f"{'Precision':>12}"
        f"{'Recall':>12}"
        f"{'F1':>12}"
    )

    print("-" * 56)

    for label, p, r, score in rows:
        print(
            f"{label:<20}"
            f"{p:>12.4f}"
            f"{r:>12.4f}"
            f"{score:>12.4f}"
        )

    print("-" * 56)

    print(
        f"{'MACRO':<20}"
        f"{precision:>12.4f}"
        f"{recall:>12.4f}"
        f"{f1:>12.4f}"
    )


def tune_threshold(split: str):
    """
    Tune NLI threshold on the SciFact development set.
    """

    thresholds = [
        0.50,
        0.55,
        0.60,
        0.65,
        0.70,
        0.75,
        0.80,
        0.85,
        0.90,
    ]

    dataset = prepare_dataset(split)

    print()
    print("# SciFact Threshold Sweep")
    print()
    print(f"Split: {split}")
    print(f"Claims: {len(dataset)}")
    print(f"Top-k retrieval: {TOP_K}")
    print()

    print(
        f"{'Threshold':<15}"
        f"{'Precision':>12}"
        f"{'Recall':>12}"
        f"{'F1':>12}"
    )

    print("-" * 51)

    best = None

    for threshold in thresholds:
        print(
            f"Running threshold {threshold:.2f}...",
            flush=True,
        )

        _, precision, recall, f1 = evaluate(
            dataset,
            threshold,
            show_progress=False,
        )

        print(
            f"{threshold:<15.2f}"
            f"{precision:>12.4f}"
            f"{recall:>12.4f}"
            f"{f1:>12.4f}"
        )

        if best is None or f1 > best["f1"]:
            best = {
                "threshold": threshold,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }

    print("-" * 51)

    print(
        "BEST "
        f"threshold={best['threshold']:.2f}, "
        f"precision={best['precision']:.4f}, "
        f"recall={best['recall']:.4f}, "
        f"F1={best['f1']:.4f}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="SciFact benchmark runner"
    )

    parser.add_argument(
        "--split",
        choices=[
            "train",
            "dev",
            "test",
        ],
        default="dev",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=NLI_THRESHOLD,
    )

    parser.add_argument(
        "--tune",
        action="store_true",
        help="Tune threshold on the selected split",
    )

    args = parser.parse_args()

    if args.tune:
        tune_threshold(args.split)
    else:
        run(
            args.split,
            args.threshold,
        )


if __name__ == "__main__":
    main()