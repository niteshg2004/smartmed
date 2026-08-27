"""
Medicine search engine: normalization + fuzzy matching against the local
Medicine catalog. Deliberately framework-light (no Django ORM calls beyond
a single queryset fetch) so it's independently unit-testable.

Handles the cases called out in the spec:
    "Dolo"            -> brand-name prefix match
    "Dolo 650"         -> brand-name + strength match
    "paracetamol"      -> generic-name match
    "paracetmol"       -> typo-tolerant fuzzy match
    "PCM 650"          -> (once PCM is stored as an alias/brand) fuzzy match

Strategy:
  1. Normalize the query the same way Medicine.normalized_search_key is
     built (medicines.models.normalize_text), so casing/punctuation never
     affects scoring.
  2. Extract a strength token (e.g. "650", "650mg") from the query if
     present, and use it to boost/penalize candidates independent of the
     fuzzy text score — strength is often the deciding factor between two
     otherwise-similar brand names.
  3. Score remaining text against brand_name, generic_name, and composition
     independently with RapidFuzz's WRatio (handles partial/word-order
     differences well), keep the best of the three per medicine.
  4. Combine into a single 0-100 confidence score and return ranked results
     above a minimum threshold.
"""
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from rapidfuzz import fuzz

from .models import Medicine, normalize_text

MIN_CONFIDENCE = 55  # below this, a match is considered noise and dropped
STRENGTH_MATCH_BONUS = 12
STRENGTH_MISMATCH_PENALTY = 15

_STRENGTH_TOKEN_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|ml|mcg|g|iu)?", re.IGNORECASE)


@dataclass
class MedicineMatch:
    medicine: Medicine
    confidence: float  # 0-100
    matched_on: str    # "brand_name" | "generic_name" | "composition"


def _extract_strength_token(text: str) -> Optional[str]:
    """Pull the first numeric(+unit) token out of a query/strength string,
    e.g. '650' from 'Dolo 650', or '650mg' from '650mg'. Returns just the
    numeric portion (unit-agnostic) so '650' matches '650mg' and '650 mg'."""
    match = _STRENGTH_TOKEN_RE.search(text)
    if not match:
        return None
    return match.group(1)


def _strip_strength(text: str) -> str:
    return _STRENGTH_TOKEN_RE.sub("", text).strip()


def search_medicines(
    query: str,
    queryset: Optional[Iterable[Medicine]] = None,
    limit: int = 10,
    min_confidence: int = MIN_CONFIDENCE,
) -> List[MedicineMatch]:
    """
    Fuzzy-search the Medicine catalog. `queryset` defaults to all Medicine
    rows — callers may pass a pre-filtered queryset (e.g. only
    prescription_required=False) to scope the search.
    """
    query = (query or "").strip()
    if not query:
        return []

    if queryset is None:
        queryset = Medicine.objects.all()
    medicines = list(queryset)
    if not medicines:
        return []

    query_strength = _extract_strength_token(query)
    query_text_only = normalize_text(_strip_strength(query))

    candidates = []  # (medicine, best_score, matched_field)
    for medicine in medicines:
        fields = {
            "brand_name": normalize_text(medicine.brand_name),
            "generic_name": normalize_text(medicine.generic_name),
            "composition": normalize_text(medicine.composition),
        }
        best_field, best_score = None, -1.0
        for field_name, field_value in fields.items():
            if not field_value:
                continue
            score = fuzz.WRatio(query_text_only or normalize_text(query), field_value)
            if score > best_score:
                best_score, best_field = score, field_name

        if best_field is None:
            continue

        confidence = best_score
        medicine_strength_token = _extract_strength_token(medicine.strength or "")
        if query_strength and medicine_strength_token:
            if query_strength == medicine_strength_token:
                confidence = min(100.0, confidence + STRENGTH_MATCH_BONUS)
            else:
                confidence = max(0.0, confidence - STRENGTH_MISMATCH_PENALTY)

        candidates.append((medicine, confidence, best_field))

    candidates.sort(key=lambda c: c[1], reverse=True)

    results = [
        MedicineMatch(medicine=m, confidence=round(score, 1), matched_on=field)
        for m, score, field in candidates
        if score >= min_confidence
    ]
    return results[:limit]
