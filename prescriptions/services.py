from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from django.db import transaction

from medicines.models import Medicine, normalize_text
from medicines.search import search_medicines

from .models import Prescription, PrescriptionMedicine
from .ocr import OCRProcessingError, OCRUnavailableError, ocr_file_to_text


STRENGTH_RE = re.compile(
    r"(?P<strength>\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml)(?:/\d+(?:\.\d+)?\s*(?:ml))?\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MedicineMatch:
    medicine: Medicine
    score: float  # 0..1
    label: str


@dataclass(frozen=True)
class DetectedMedicine:
    extracted_name: str
    extracted_strength: str
    best_match: Optional[MedicineMatch]
    alternatives: Sequence[MedicineMatch]


def _iter_candidate_lines(text: str) -> Iterable[str]:
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        # Drop very short / likely-non-medicine noise.
        if len(line) < 4:
            continue
        # Keep lines that have at least a couple of letters.
        if len(re.findall(r"[a-zA-Z]", line)) < 3:
            continue
        yield line


def _extract_strength(line: str) -> str:
    m = STRENGTH_RE.search(line or "")
    return (m.group("strength") if m else "").strip()


def _wrap_search_result(result) -> MedicineMatch:
    return MedicineMatch(
        medicine=result.medicine,
        score=round(float(result.confidence) / 100.0, 4),
        label=f"{result.medicine.brand_name} {result.medicine.strength}",
    )


def _serialize_detected_item(item: PrescriptionMedicine) -> dict:
    alternatives = []
    query = " ".join(part for part in [item.extracted_name, item.extracted_strength] if part).strip()
    for result in search_medicines(query or item.extracted_name, limit=5, min_confidence=45):
        if item.medicine_id and result.medicine.id == item.medicine_id:
            continue
        alternatives.append(_wrap_search_result(result))

    approved_alternatives = []
    candidate_rows = []
    # Only show (and generate) alternative candidates after explicit user confirmation.
    if item.medicine_id and item.user_confirmed:
        try:
            from alternatives.models import AlternativeCandidate
            from alternatives.services import sync_alternative_candidates_for_medicine

            # Ensure we have up-to-date candidate rows, but do not block the prescription UI if
            # alternatives fail (e.g. app not migrated yet in some environments).
            sync_alternative_candidates_for_medicine(item.medicine, limit=5)

            queryset = (
                AlternativeCandidate.objects.filter(medicine=item.medicine)
                .select_related("candidate_medicine", "verified_by")
                .exclude(verification_status=AlternativeCandidate.VerificationStatus.REJECTED)
                .order_by("-confidence_score")[:5]
            )
            candidate_rows = list(queryset)

            approved_alternatives = [
                row for row in candidate_rows if row.verification_status == AlternativeCandidate.VerificationStatus.APPROVED
            ]
        except Exception:  # pragma: no cover - alternatives should not block OCR workflow
            approved_alternatives = []
            candidate_rows = []

    return {
        "obj": item,
        "alternatives": alternatives,
        "candidates": candidate_rows,
        "approved_alternatives": approved_alternatives,
        "confidence_pct": int(round(item.match_confidence * 100)),
    }


def detect_medicines_from_text(
    text: str,
    *,
    min_confidence: float = 0.65,
    limit_lines: int = 20,
    max_alternatives: int = 5,
) -> List[DetectedMedicine]:
    """
    Heuristic OCR -> medicine matching step.

    This is intentionally conservative: OCR output is noisy, and we only
    surface candidates to the user for confirmation.
    """

    detected: List[DetectedMedicine] = []
    for idx, line in enumerate(_iter_candidate_lines(text)):
        if idx >= limit_lines:
            break

        strength = _extract_strength(line)
        query = normalize_text(line)
        if not query:
            continue

        search_results = search_medicines(line, limit=max_alternatives, min_confidence=int(min_confidence * 100))
        alternatives = [_wrap_search_result(result) for result in search_results]
        best = alternatives[0] if alternatives else None

        # Only surface if there's a decent match signal OR a strength token.
        if best and (best.score >= min_confidence or strength):
            detected.append(
                DetectedMedicine(
                    extracted_name=line[:255],
                    extracted_strength=strength[:50],
                    best_match=best,
                    alternatives=alternatives,
                )
            )

    # De-duplicate very similar extracted names (common OCR repeats).
    seen = set()
    unique: List[DetectedMedicine] = []
    for item in detected:
        key = normalize_text(item.extracted_name)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


@transaction.atomic
def process_prescription(prescription: Prescription, *, force: bool = False) -> Prescription:
    if (
        prescription.processing_status == Prescription.ProcessingStatus.PROCESSED
        and prescription.detected_medicines.exists()
        and not force
    ):
        return prescription

    if force:
        prescription.detected_medicines.all().delete()
        prescription.processing_status = Prescription.ProcessingStatus.PENDING

    try:
        result = ocr_file_to_text(prescription.uploaded_file.path)
        if not result.text.strip():
            raise OCRProcessingError(
                "No text could be extracted from this image. Please upload a clearer prescription image."
            )
        prescription.extracted_text = result.text
        prescription.processing_error = ""
        prescription.processing_status = Prescription.ProcessingStatus.PROCESSED
        prescription.save(update_fields=["extracted_text", "processing_error", "processing_status"])

        if not prescription.detected_medicines.exists():
            detected = detect_medicines_from_text(result.text)
            for item in detected:
                best = item.best_match
                detected_item = PrescriptionMedicine.objects.create(
                    prescription=prescription,
                    extracted_name=item.extracted_name,
                    extracted_strength=item.extracted_strength,
                    medicine=best.medicine if best else None,
                    match_confidence=best.score if best else 0.0,
                    user_confirmed=False,
                )
    except OCRUnavailableError as exc:
        prescription.processing_status = Prescription.ProcessingStatus.FAILED
        prescription.processing_error = (
            f"{exc} Install Tesseract OCR and set `OCR_PATH` in `.env` if the binary is not on PATH."
        )
        prescription.save(update_fields=["processing_status", "processing_error"])
    except OCRProcessingError as exc:
        prescription.processing_status = Prescription.ProcessingStatus.FAILED
        prescription.processing_error = str(exc)
        prescription.save(update_fields=["processing_status", "processing_error"])

    return prescription


def get_prescription_detected_rows(prescription: Prescription) -> List[dict]:
    rows = []
    for item in prescription.detected_medicines.select_related("medicine").all():
        rows.append(_serialize_detected_item(item))
    return rows


@transaction.atomic
def save_prescription_confirmations(
    prescription: Prescription,
    selections: dict[int, dict],
) -> List[PrescriptionMedicine]:
    updated_items = []
    for item in prescription.detected_medicines.select_related("medicine").all():
        payload = selections.get(item.pk, {})
        confirmed = bool(payload.get("confirmed"))
        medicine_id = payload.get("medicine_id")

        item.user_confirmed = confirmed
        item.confirmation_status = (
            PrescriptionMedicine.ConfirmationStatus.CONFIRMED
            if confirmed
            else PrescriptionMedicine.ConfirmationStatus.REJECTED
        )
        if medicine_id in ("", None, 0, "0"):
            item.medicine = None
            item.match_confidence = 0.0
        elif medicine_id:
            try:
                medicine_id = int(medicine_id)
            except (TypeError, ValueError):
                medicine_id = None
            if medicine_id:
                result = search_medicines(item.extracted_name, queryset=Medicine.objects.filter(pk=medicine_id), limit=1)
                item.medicine = Medicine.objects.filter(pk=medicine_id).first()
                item.match_confidence = round(float(result[0].confidence) / 100.0, 4) if result else 1.0
                if item.medicine_id and confirmed:
                    try:
                        from alternatives.services import sync_alternative_candidates_for_medicine

                        sync_alternative_candidates_for_medicine(item.medicine, limit=5)
                    except Exception:
                        pass

        item.save(update_fields=["user_confirmed", "confirmation_status", "medicine", "match_confidence"])
        updated_items.append(item)
    return updated_items
