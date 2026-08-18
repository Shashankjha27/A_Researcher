from datetime import datetime, timezone
from uuid import uuid4

from app.nli.direction_check import check_direction
from app.schemas import ClaimPairVerdict, Relation
from config import NLI_MODEL, NLI_THRESHOLD


def build_pair_verdict(
    claim_id_a: str,
    claim_id_b: str,
    text_a: str,
    text_b: str,
    threshold: float = NLI_THRESHOLD,
) -> ClaimPairVerdict:
    is_contradiction, _label, probability = check_direction(
        text_a,
        text_b,
        threshold=threshold,
    )

    relation = (
        Relation.CONTRADICTION
        if is_contradiction
        else Relation.SUPPORT
    )

    return ClaimPairVerdict(
        pair_id=str(uuid4()),
        claim_id_a=claim_id_a,
        claim_id_b=claim_id_b,
        relation=relation,
        confidence_score=probability,
        nli_probability=probability,
        nli_model=NLI_MODEL,
        threshold=threshold,
        checked_at=datetime.now(timezone.utc),
    )