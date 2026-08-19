from __future__ import annotations

from pathlib import Path
from typing import Any

from app.flags.runner import run_flags
from app.llm.client import get_llm_call
from app.nli.pair_reduction import build_candidate_pairs
from app.nli.verdict import build_pair_verdict
from app.pipeline.extract import extract_claims_from_chunk
from app.pipeline.ingest import ingest_paper
from app.retrieval.evidence import retrieve_evidence
from app.scoring.confidence import confidence_from_signals
from app.scoring.report_builder import build_report
from app.scoring.verdict import determine_verdict
from app.store.doc_store import DocStore


def run_pipeline(
    paper_path: str | Path,
    *,
    paper_id: str,
    title: str,
    authors: list[str],
    year: int,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    evidence_top_k: int = 5,
    pair_threshold: float = 0.75,
    nli_threshold: float | None = None,
    store: DocStore | None = None,
) -> dict[str, Any]:

    store = store or DocStore()

    paper = ingest_paper(
        paper_path,
        paper_id=paper_id,
        title=title,
        authors=authors,
        year=year,
    )

    store.save("papers", paper)

    llm_call = get_llm_call(
        provider=provider,
        model=model,
        api_key=api_key,
    )

    claims = []

    for block in paper.blocks:
        block_claims = extract_claims_from_chunk(
            llm_call=llm_call,
            chunk_text=block.text,
            paper_id=paper.paper_id,
            section=block.section,
            chunk_start_offset=block.start_offset,
        )

        claims.extend(block_claims)

    for claim in claims:
        store.save("claims", claim)

    if not claims:
        report = build_report([], title=paper.title)

        return {
            "paper": paper.model_dump(),
            "claims": [],
            "pair_verdicts": [],
            "report": report,
        }

    all_sentences: list[str] = []

    for block in paper.blocks:
        sentences = [
            sentence.strip() for sentence in block.text.split(".") if sentence.strip()
        ]

        all_sentences.extend(sentences)

    claim_records: dict[str, dict[str, Any]] = {}

    for claim in claims:
        evidence = retrieve_evidence(
            claim.claim_text,
            all_sentences,
            top_k=evidence_top_k,
        )

        supporting_evidence = [
            {
                "paper_id": paper.paper_id,
                "text": text,
                "score": score,
            }
            for text, score in evidence
        ]

        claim_records[claim.claim_id] = {
            "claim_id": claim.claim_id,
            "paper_id": claim.paper_id,
            "claim_text": claim.claim_text,
            "effect_direction": claim.effect_direction.value,
            "method_type": claim.method_type.value,
            "sample_size": claim.sample_size,
            "source_sentence": claim.provenance.source_sentence,
            "start_offset": claim.provenance.start_offset,
            "end_offset": claim.provenance.end_offset,
            "supporting_evidence": supporting_evidence,
            "contradicting_evidence": [],
            "citation_chains": [],
            "reference_id": None,
        }

    claim_texts = [claim.claim_text for claim in claims]

    candidate_pairs = build_candidate_pairs(
        claim_texts,
        threshold=pair_threshold,
    )

    pair_verdicts = []

    for index_a, index_b in candidate_pairs:
        claim_a = claims[index_a]
        claim_b = claims[index_b]

        kwargs: dict[str, float] = {}

        if nli_threshold is not None:
            kwargs["threshold"] = nli_threshold

        verdict = build_pair_verdict(
            claim_id_a=claim_a.claim_id,
            claim_id_b=claim_b.claim_id,
            text_a=claim_a.claim_text,
            text_b=claim_b.claim_text,
            **kwargs,
        )

        pair_verdicts.append(verdict)

        store.save(
            "pair_verdicts",
            verdict,
        )

        if verdict.relation.value == "contradiction":
            claim_records[claim_a.claim_id]["contradicting_evidence"].append(
                {
                    "paper_id": claim_b.paper_id,
                    "text": claim_b.provenance.source_sentence,
                    "score": verdict.nli_probability,
                }
            )

            claim_records[claim_b.claim_id]["contradicting_evidence"].append(
                {
                    "paper_id": claim_a.paper_id,
                    "text": claim_a.provenance.source_sentence,
                    "score": verdict.nli_probability,
                }
            )

    for claim in claims:
        record = claim_records[claim.claim_id]

        evidence_scores = [
            float(item["score"]) for item in record["supporting_evidence"]
        ]

        contradictions = [
            pair
            for pair in pair_verdicts
            if (
                pair.relation.value == "contradiction"
                and (
                    pair.claim_id_a == claim.claim_id
                    or pair.claim_id_b == claim.claim_id
                )
            )
        ]

        supports = [
            pair
            for pair in pair_verdicts
            if (
                pair.relation.value == "support"
                and (
                    pair.claim_id_a == claim.claim_id
                    or pair.claim_id_b == claim.claim_id
                )
            )
        ]

        total_pairs = len(supports) + len(contradictions)

        if total_pairs:
            agreement = 1.0 if not contradictions else 0.0
        else:
            agreement = 0.0

        if contradictions:
            nli_probability = max(pair.nli_probability for pair in contradictions)
        elif supports:
            nli_probability = max(pair.nli_probability for pair in supports)
        else:
            nli_probability = (
                sum(evidence_scores) / len(evidence_scores) if evidence_scores else 0.0
            )

        confidence, components = confidence_from_signals(
            nli_probability=nli_probability,
            evidence_scores=evidence_scores,
            agreement=agreement,
        )

        verdict = determine_verdict(
            confidence=confidence,
            support_count=len(supports),
            contradiction_count=len(contradictions),
        )

        record["confidence_score"] = confidence
        record["confidence_components"] = components
        record["verdict"] = verdict.value

        flags = run_flags(
            record,
            known_references=set(),
            retracted_references=set(),
        )

        record["flags"] = flags

        claim.confidence_score = confidence
        claim.confidence_components = components

    for claim in claims:
        store.save("claims", claim)

    report = build_report(
        list(claim_records.values()),
        title=paper.title,
    )

    return {
        "paper": paper.model_dump(),
        "claims": [claim_records[claim.claim_id] for claim in claims],
        "pair_verdicts": [verdict.model_dump() for verdict in pair_verdicts],
        "report": report,
    }
