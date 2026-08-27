from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List

from django.db import transaction
from django.utils import timezone

from medicines.models import Medicine, normalize_text

from .models import AlternativeCandidate

STRENGTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu)?", re.IGNORECASE)


@dataclass(frozen=True)
class CandidateScore:
    candidate: Medicine
    similarity_score: float
    matching_basis: str
    rationale: str


def _token_set(value: str) -> set[str]:
    return {token for token in normalize_text(value).split() if token}


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _strength_similarity(source: str, target: str) -> float:
    source_match = STRENGTH_RE.search(source or "")
    target_match = STRENGTH_RE.search(target or "")
    if not source_match or not target_match:
        return 0.0

    source_value, source_unit = source_match.group(1), (source_match.group(2) or "").lower()
    target_value, target_unit = target_match.group(1), (target_match.group(2) or "").lower()
    if source_value == target_value and source_unit == target_unit:
        return 1.0
    if source_value == target_value:
        return 0.9
    try:
        source_num = float(source_value)
        target_num = float(target_value)
    except ValueError:
        return 0.0

    delta = abs(source_num - target_num) / max(source_num, target_num, 1.0)
    return max(0.0, 1.0 - delta)


def _dosage_similarity(source: str, target: str) -> float:
    return 1.0 if source and target and source == target else 0.0


def _category_similarity(source: str, target: str) -> float:
    return _jaccard(_token_set(source), _token_set(target))


def _composition_similarity(source: Medicine, target: Medicine) -> float:
    composition = _jaccard(_token_set(source.composition), _token_set(target.composition))
    active_ingredient = _jaccard(_token_set(source.generic_name), _token_set(target.generic_name))
    return max(composition, active_ingredient)


def _build_score(source: Medicine, candidate: Medicine) -> CandidateScore:
    composition_score = _composition_similarity(source, candidate)
    active_score = _jaccard(_token_set(source.generic_name), _token_set(candidate.generic_name))
    strength_score = _strength_similarity(source.strength, candidate.strength)
    dosage_score = _dosage_similarity(source.dosage_form, candidate.dosage_form)
    category_score = _category_similarity(source.therapeutic_category, candidate.therapeutic_category)

    weighted = (
        (composition_score * 0.35)
        + (active_score * 0.20)
        + (strength_score * 0.20)
        + (dosage_score * 0.15)
        + (category_score * 0.10)
    )

    strong_axes = sum(
        1
        for value in [composition_score, active_score, strength_score, dosage_score, category_score]
        if value >= 0.75
    )
    if strong_axes >= 2:
        basis = AlternativeCandidate.MatchingBasis.COMBINED
    else:
        ranked = [
            (composition_score, AlternativeCandidate.MatchingBasis.COMPOSITION),
            (strength_score, AlternativeCandidate.MatchingBasis.STRENGTH),
            (dosage_score, AlternativeCandidate.MatchingBasis.DOSAGE_FORM),
            (category_score, AlternativeCandidate.MatchingBasis.THERAPEUTIC_CATEGORY),
        ]
        basis = max(ranked, key=lambda item: item[0])[1]

    rationale_parts = []
    if composition_score >= 0.7:
        rationale_parts.append("composition/active ingredient overlap")
    if strength_score >= 0.9:
        rationale_parts.append("matching strength")
    if dosage_score >= 1.0:
        rationale_parts.append("same dosage form")
    if category_score >= 0.6:
        rationale_parts.append("similar therapeutic category")
    rationale = ", ".join(rationale_parts) or "partial structured attribute similarity"

    return CandidateScore(
        candidate=candidate,
        similarity_score=round(weighted, 4),
        matching_basis=basis,
        rationale=rationale,
    )


def rank_alternative_medicines(
    medicine: Medicine,
    *,
    queryset=None,
    limit: int = 5,
    min_similarity: float = 0.55,
) -> List[CandidateScore]:
    queryset = queryset or Medicine.objects.exclude(pk=medicine.pk)
    candidates = []
    for candidate in queryset:
        score = _build_score(medicine, candidate)
        if score.similarity_score >= min_similarity:
            candidates.append(score)

    candidates.sort(key=lambda item: item.similarity_score, reverse=True)
    return candidates[:limit]


@transaction.atomic
def sync_alternative_candidates_for_medicine(medicine: Medicine, *, limit: int = 5) -> List[AlternativeCandidate]:
    ranked = rank_alternative_medicines(medicine, limit=limit)
    stored = []
    seen_ids = set()
    for score in ranked:
        candidate, _created = AlternativeCandidate.objects.update_or_create(
            medicine=medicine,
            candidate_medicine=score.candidate,
            defaults={
                "matching_basis": score.matching_basis,
                "confidence_score": score.similarity_score,
            },
        )
        stored.append(candidate)
        seen_ids.add(score.candidate.id)

    # Keep verified historical records unless the candidate still exists; trim only pending noise.
    AlternativeCandidate.objects.filter(
        medicine=medicine,
        verification_status=AlternativeCandidate.VerificationStatus.PENDING,
    ).exclude(candidate_medicine_id__in=seen_ids).delete()
    return stored


def get_verified_alternatives_for_medicine(medicine: Medicine, *, limit: int = 5):
    sync_alternative_candidates_for_medicine(medicine, limit=limit)
    return (
        AlternativeCandidate.objects.filter(
            medicine=medicine,
            verification_status=AlternativeCandidate.VerificationStatus.APPROVED,
        )
        .select_related("candidate_medicine", "verified_by")
        .order_by("-confidence_score")[:limit]
    )


def review_alternative_candidate(candidate: AlternativeCandidate, *, user, approve: bool) -> AlternativeCandidate:
    candidate.verification_status = (
        AlternativeCandidate.VerificationStatus.APPROVED
        if approve
        else AlternativeCandidate.VerificationStatus.REJECTED
    )
    candidate.verified_by = user
    candidate.verified_at = timezone.now()
    candidate.save(update_fields=["verification_status", "verified_by", "verified_at"])
    return candidate
