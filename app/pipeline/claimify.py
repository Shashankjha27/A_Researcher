from __future__ import annotations

import re

from app.pipeline.ingest import split_sentences

_EMPIRICAL_PATTERNS = (
    (r"\b(increased|decreased|improved|reduced|enhanced|inhibited|"
    r"associated|correlated|predicted|outperformed|achieved|observed|"
    r"found|yielded|resulted|caused|affected)\b"),
    r"\b\d+(?:\.\d+)?\s*%\b",
    r"\bp\s*(?:<|>|=)\s*0?\.\d+\b",
    r"\b(auc|auc-roc|auc-pr|accuracy|precision|recall|f1|specificity)\b",
    r"\b(significant|significantly)\b",
)

_PRONOUN_PATTERNS = re.compile(
    r"^(this|that|these|those|it|they|their)\b",
    re.IGNORECASE,
)

_CLAUSE_SPLIT_RE = re.compile(
    r"\s+\b(?:and|while|whereas|but|however)\b\s+",
    re.IGNORECASE,
)

_VERBS = (
    r"improved|increased|decreased|reduced|enhanced|"
    r"outperformed|achieved|showed|demonstrated|"
    r"yielded|resulted|caused|affected|"
    r"predicted|correlated|associated|"
    r"had|exhibited|observed"
)

_EMPIRICAL_REGEX = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in _EMPIRICAL_PATTERNS
)


def split_claim_sentences(
    chunk_text: str,
) -> list[tuple[str, int, int]]:
    """Stage 1: split the chunk into sentences with original offsets."""
    return split_sentences(chunk_text)


def select_candidate_sentences(
    sentences: list[tuple[str, int, int]],
) -> list[tuple[str, int, int]]:
    """Stage 2: retain sentences likely to contain empirical findings."""
    return [
        (sentence, start, end)
        for sentence, start, end in sentences
        if any(pattern.search(sentence) for pattern in _EMPIRICAL_REGEX)
    ]


def disambiguate_sentences(
    sentences: list[tuple[str, int, int]],
) -> list[tuple[str, int, int]]:
    """
    Stage 3: conservatively resolve sentence-internal ambiguity.

    Selection is intentionally not repeated here. This stage should operate
    on candidates already chosen by select_candidate_sentences().
    """
    result: list[tuple[str, int, int]] = []

    for sentence, start, end in sentences:
        cleaned = sentence.strip()

        if not cleaned:
            continue

        # Remove citation markers such as [1], [2,3], [12–14].
        cleaned = re.sub(
            r"\s*\[(?:\d+(?:\s*[-–,]\s*\d+)*)+\]",
            "",
            cleaned,
        )

        # Leave pronoun resolution to the LLM when it requires context.
        # Do not invent a subject here.
        result.append((cleaned, start, end))

    return result


def _find_subject(sentence: str) -> str | None:
    """
    Extract a conservative subject candidate from the beginning of a sentence.

    Examples:
        'The treatment improved...' -> 'The treatment'
        'STG-NF achieved...'       -> 'STG-NF'
    """
    match = re.match(
        r"^(?P<subject>(?:The|A|An)\s+[^,;]+?|[A-Z][A-Za-z0-9_-]*(?:\s+[A-Za-z0-9_-]+){0,4})\s+"
        rf"(?:{_VERBS})\b",
        sentence,
        re.IGNORECASE,
    )

    if match:
        return match.group("subject").strip()

    return None


def decompose_sentences(
    sentences: list[tuple[str, int, int]],
) -> list[tuple[str, int, int]]:
    """
    Stage 4: split multi-result sentences into standalone claims.

    Insert the original subject into coordinated clauses when the clause
    would otherwise become a subject-less fragment.

    Offsets always refer to the original source sentence span because the
    decontextualized text may contain inserted words.
    """
    result: list[tuple[str, int, int]] = []

    for sentence, start, end in sentences:
        parts = _CLAUSE_SPLIT_RE.split(sentence)

        if len(parts) == 1:
            result.append((sentence, start, end))
            continue

        subject = _find_subject(sentence)

        for index, part in enumerate(parts):
            part = part.strip()

            if not part:
                continue

            if index == 0:
                claim = part
            elif subject and re.match(
                rf"^(?:{_VERBS})\b",
                part,
                re.IGNORECASE,
            ):
                claim = f"{subject} {part}"
            else:
                claim = part

            claim = claim.rstrip(".!?") + "."

            result.append((claim, start, end))

    return result


def build_claimify_candidates(
    chunk_text: str,
) -> list[tuple[str, int, int]]:
    """Run the complete Claimify preprocessing pipeline."""
    sentences = split_claim_sentences(chunk_text)
    selected = select_candidate_sentences(sentences)
    disambiguated = disambiguate_sentences(selected)
    return decompose_sentences(disambiguated)


def build_claimify_context(
    chunk_text: str,
) -> str:
    """Return decontextualized candidate claims for the LLM prompt."""
    candidates = build_claimify_candidates(chunk_text)

    return "\n".join(
        sentence
        for sentence, _, _ in candidates
    )
