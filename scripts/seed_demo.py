"""Build the checked-in demo fixture deterministically (no LLM).

Runs the REAL ingest -> evidence -> NLI -> scoring stages of the
pipeline over data/demo/golden_contradiction.txt with hand-authored
claims (extraction is the only non-deterministic stage, so it is
replaced by fixed claim definitions). The NLI pair verdict and
confidence scores are computed by the production code paths.

Writes JSONL fixtures under data/demo/ that ship with the repo;
app startup imports them when the demo paper is missing (see
app/store/demo_seed.py).

Usage: .venv/bin/python scripts/seed_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.flags.runner import run_flags
from app.nli.evidence_check import evidence_support_counts
from app.nli.pair_reduction import build_candidate_pairs
from app.nli.verdict import build_pair_verdict
from app.pipeline.ingest import ingest_paper, split_sentences
from app.retrieval.evidence import retrieve_evidence
from app.schemas.enums import EffectDirection, MethodType
from app.schemas.schemas import Claim, Provenance
from app.scoring.confidence import confidence_from_signals
from app.scoring.verdict import determine_verdict
from config import NLI_THRESHOLD

DEMO_PAPER_ID = "paper-demo-golden"
DEMO_DIR = Path("data/demo")
SOURCE_TXT = DEMO_DIR / "golden_contradiction.txt"

TITLE = "Recovery Outcomes After Adjuvant Treatment (Demo)"
AUTHORS = ["A. Author", "B. Author"]
YEAR = 2024

# (sentence prefix, method_type, effect_direction, sample_size)
CLAIM_SPECS = [
    (
        "The treatment significantly improves",
        MethodType.RCT,
        EffectDirection.POSITIVE,
        None,
    ),
    (
        "A re-analysis found",
        MethodType.OBSERVATIONAL,
        EffectDirection.NEGATIVE,
        None,
    ),
    (
        "Hospital records show",
        MethodType.OBSERVATIONAL,
        EffectDirection.POSITIVE,
        None,
    ),
    (
        "The pooled sample included",
        MethodType.OTHER,
        EffectDirection.NULL_EFFECT,
        40,
    ),
]


def main() -> None:
    paper = ingest_paper(
        SOURCE_TXT,
        paper_id=DEMO_PAPER_ID,
        title=TITLE,
        authors=AUTHORS,
        year=YEAR,
    )

    sentences: list[tuple[str, int]] = []

    for block_index, block in enumerate(paper.blocks):
        for text, start, end in split_sentences(block.text):
            sentences.append(
                (text, block.start_offset + start),
            )

    claims: list[Claim] = []

    for index, (prefix, method_type, effect_direction, sample_size) in enumerate(CLAIM_SPECS):
        match = next(
            (
                (text, offset)
                for text, offset in sentences
                if text.startswith(prefix)
            ),
            None,
        )

        if match is None:
            raise SystemExit(f"sentence not found: {prefix!r}")

        text, offset = match

        claims.append(
            Claim(
                claim_id=f"cl_{DEMO_PAPER_ID}_demo_0_{index}",
                paper_id=DEMO_PAPER_ID,
                claim_text=text,
                method_type=method_type,
                effect_direction=effect_direction,
                sample_size=sample_size,
                provenance=Provenance(
                    source_sentence=text,
                    start_offset=offset,
                    end_offset=offset + len(text),
                ),
            ),
        )

    # Title-like fragments are excluded from the evidence pool:
    # NLI against bare titles is noise. Merged title+intro fragments
    # (containing a blank line) and punctuation-less headers both go.
    all_sentence_texts = [
        text
        for text, _ in sentences
        if "\n\n" not in text
        and text.rstrip().endswith((".", "!", "?"))
    ]

    records: dict[str, dict] = {}

    for claim in claims:
        evidence = retrieve_evidence(
            claim.claim_text,
            all_sentence_texts,
            top_k=5,
        )

        records[claim.claim_id] = {
            "claim_id": claim.claim_id,
            "paper_id": claim.paper_id,
            "claim_text": claim.claim_text,
            "effect_direction": claim.effect_direction.value,
            "method_type": claim.method_type.value,
            "sample_size": claim.sample_size,
            "source_sentence": claim.provenance.source_sentence,
            "start_offset": claim.provenance.start_offset,
            "end_offset": claim.provenance.end_offset,
            "supporting_evidence": [
                {
                    "paper_id": DEMO_PAPER_ID,
                    "text": text,
                    "score": score,
                }
                for text, score in evidence
            ],
            "contradicting_evidence": [],
            "citation_chains": [],
            "reference_id": None,
        }

    candidate_pairs = build_candidate_pairs(
        [claim.claim_text for claim in claims],
        threshold=0.75,
    )

    pair_verdicts = []

    for index_a, index_b in candidate_pairs:
        claim_a = claims[index_a]
        claim_b = claims[index_b]

        verdict = build_pair_verdict(
            claim_id_a=claim_a.claim_id,
            claim_id_b=claim_b.claim_id,
            text_a=claim_a.claim_text,
            text_b=claim_b.claim_text,
        )

        pair_verdicts.append(verdict)

        print(
            f"pair {index_a}<->{index_b}: {verdict.relation.value}"
            f" @ {verdict.nli_probability:.3f}"
        )

        if verdict.relation.value == "contradiction":
            records[claim_a.claim_id]["contradicting_evidence"].append(
                {
                    "paper_id": claim_b.paper_id,
                    "text": claim_b.provenance.source_sentence,
                    "score": verdict.nli_probability,
                },
            )

            records[claim_b.claim_id]["contradicting_evidence"].append(
                {
                    "paper_id": claim_a.paper_id,
                    "text": claim_a.provenance.source_sentence,
                    "score": verdict.nli_probability,
                },
            )

    for claim in claims:
        record = records[claim.claim_id]

        support_count, contradiction_count, firing_probability = (
            evidence_support_counts(
                claim_text=record["claim_text"],
                evidence_texts=[
                    item["text"]
                    for item in record["supporting_evidence"]
                ],
                threshold=NLI_THRESHOLD,
            )
        )

        record["evidence_support_count"] = support_count
        record["evidence_contradiction_count"] = contradiction_count
        record["evidence_nli_probability"] = firing_probability

        contradictions = [
            pair
            for pair in pair_verdicts
            if (
                pair.relation.value == "contradiction"
                and claim.claim_id in (pair.claim_id_a, pair.claim_id_b)
            )
        ]

        supports = [
            pair
            for pair in pair_verdicts
            if (
                pair.relation.value == "support"
                and claim.claim_id in (pair.claim_id_a, pair.claim_id_b)
            )
        ]

        support_total = len(supports) + support_count
        contradiction_total = len(contradictions) + contradiction_count

        total_pairs = support_total + contradiction_total

        agreement = (
            (1.0 if not contradiction_total else 0.0)
            if total_pairs
            else 0.0
        )

        evidence_scores = [
            float(item["score"])
            for item in record["supporting_evidence"]
        ]

        contradiction_probs = [
            pair.nli_probability for pair in contradictions
        ]
        support_probs = [pair.nli_probability for pair in supports]

        if record["evidence_contradiction_count"]:
            contradiction_probs.append(
                record["evidence_nli_probability"],
            )

        if record["evidence_support_count"]:
            support_probs.append(record["evidence_nli_probability"])

        if contradiction_probs:
            nli_probability = max(contradiction_probs)
        elif support_probs:
            nli_probability = max(support_probs)
        else:
            nli_probability = (
                sum(evidence_scores) / len(evidence_scores)
                if evidence_scores
                else 0.0
            )

        confidence, components = confidence_from_signals(
            nli_probability=nli_probability,
            evidence_scores=evidence_scores,
            agreement=agreement,
        )

        verdict_value = determine_verdict(
            confidence=confidence,
            support_count=support_total,
            contradiction_count=contradiction_total,
        )

        record["support_count"] = support_total
        record["contradiction_count"] = contradiction_total
        record["confidence_score"] = confidence
        record["confidence_components"] = components
        record["verdict"] = verdict_value.value

        record["flags"] = run_flags(
            record,
            known_references=set(),
            retracted_references=set(),
            paper_funding_source=paper.funding_source,
        )

        claim.confidence_score = confidence
        claim.confidence_components = components
        claim.support_count = support_total
        claim.contradiction_count = contradiction_total
        claim.verdict = verdict_value
        claim.supporting_evidence = record["supporting_evidence"]
        claim.contradicting_evidence = record["contradicting_evidence"]

        print(
            f"{claim.claim_id[-14:]}: {verdict_value.value}"
            f" (conf {confidence:.2f}, sup {support_total},"
            f" con {contradiction_total})"
        )

    fixtures = {
        "papers": [paper],
        "claims": claims,
        "pair_verdicts": pair_verdicts,
    }

    for entity, models in fixtures.items():
        out_path = DEMO_DIR / f"demo_fixture_{entity}.jsonl"

        out_path.write_text(
            "\n".join(model.model_dump_json() for model in models)
            + ("\n" if models else ""),
        )

        print(f"wrote {len(models)} {entity} -> {out_path}")


if __name__ == "__main__":
    main()
