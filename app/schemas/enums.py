from enum import Enum


class MethodType(str, Enum):
    RCT = "RCT"
    OBSERVATIONAL = "observational"
    META_ANALYSIS = "meta-analysis"
    OTHER = "other"


class EffectDirection(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NULL_EFFECT = "null_effect"
    MIXED = "mixed"


class RetractionStatus(str, Enum):
    ACTIVE = "active"
    RETRACTED = "retracted"
    UNKNOWN = "unknown"


class Relation(str, Enum):
    CONTRADICTION = "contradiction"
    SUPPORT = "support"
    NEUTRAL = "neutral"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FlagType(str, Enum):
    SMALL_SAMPLE = "small_sample"
    SINGLE_STUDY_AS_CONSENSUS = "single_study_as_consensus"
    FUNDING_CONFLICT = "funding_conflict"
    CITATION_LAUNDERING = "citation_laundering"
    RETRACTED = "retracted"
    REFERENCE_CHECK = "reference_check"


class SourceType(str, Enum):
    PDF = "pdf"
    TEXT = "text"
    PUBMED = "pubmed"
