from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.enums import (
    EffectDirection,
    FlagType,
    MethodType,
    Relation,
    RetractionStatus,
    Severity,
    SourceType,
)
from app.scoring.verdict import Verdict


class Block(BaseModel):
    section: str
    text: str
    start_offset: int
    end_offset: int

class Paper(BaseModel):
    paper_id: str
    title: str
    authors: list[str]
    year: int
    source: SourceType
    path: str
    ingested_at: datetime
    doi: str | None = None
    journal: str | None = None
    funding_source: str | None = None
    retraction_status: RetractionStatus = RetractionStatus.UNKNOWN
    blocks: list[Block] = []

class Provenance(BaseModel):
    source_sentence: str
    start_offset: int
    end_offset: int

class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    paper_id: str
    claim_text: str
    method_type: MethodType
    effect_direction: EffectDirection
    provenance: Provenance
    sample_size: int | None = None
    confidence_components: dict[str, float] = {}
    confidence_score: float = 0.0
    support_count: int = 0
    contradiction_count: int = 0
    verdict: Verdict | None = None
    supporting_evidence: list[dict] = []
    contradicting_evidence: list[dict] = []

class ClaimPairVerdict(BaseModel):
    pair_id: str
    claim_id_a: str
    claim_id_b: str
    relation: Relation
    confidence_score: float
    nli_probability: float
    nli_model: str
    threshold: float
    checked_at: datetime

class Flag(BaseModel):
    flag_id: str
    claim_id: str
    flag_type: FlagType
    severity: Severity
    rationale_string: str

class DebateTurn(BaseModel):
    role: str
    text: str

class DebateRecord(BaseModel):
    debate_id: str
    claim_id: str
    paper_id: str
    model: str
    rounds: int
    turns: list[DebateTurn]
    judge_verdict: Verdict
    judge_rationale: str
    created_at: datetime

class VerdictOverride(BaseModel):
    override_id: str
    claim_id: str
    paper_id: str
    original_verdict: Verdict | None = None
    overridden_verdict: Verdict
    note: str | None = None
    created_at: datetime

class FlagReview(BaseModel):
    review_id: str
    flag_id: str
    claim_id: str
    accepted: bool
    created_at: datetime
