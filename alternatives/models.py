from django.conf import settings
from django.db import models

from medicines.models import Medicine


class AlternativeCandidate(models.Model):
    """
    A *candidate* match between two medicines based on attribute similarity
    (composition/strength/dosage-form/category) — never an automatic
    substitution recommendation. Only `verification_status = approved`
    candidates, set by an admin/pharmacist with `can_verify_alternatives`,
    may be surfaced to patients as "professionally verified". See Section 9.
    """

    class MatchingBasis(models.TextChoices):
        COMPOSITION = "composition", "Composition"
        STRENGTH = "strength", "Strength"
        DOSAGE_FORM = "dosage_form", "Dosage Form"
        THERAPEUTIC_CATEGORY = "therapeutic_category", "Therapeutic Category"
        COMBINED = "combined", "Combined Attributes"

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    medicine = models.ForeignKey(
        Medicine, on_delete=models.CASCADE, related_name="alternative_candidates_for"
    )
    candidate_medicine = models.ForeignKey(
        Medicine, on_delete=models.CASCADE, related_name="alternative_candidate_of"
    )
    matching_basis = models.CharField(max_length=30, choices=MatchingBasis.choices)
    confidence_score = models.FloatField(help_text="0.0–1.0 attribute-similarity score, not a clinical rating.")
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_alternatives",
        limit_choices_to={"role": "admin"},
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-confidence_score"]
        constraints = [
            models.UniqueConstraint(
                fields=["medicine", "candidate_medicine"], name="unique_medicine_candidate_pair"
            ),
            models.CheckConstraint(
                check=~models.Q(medicine=models.F("candidate_medicine")),
                name="candidate_must_differ_from_medicine",
            ),
        ]
        indexes = [
            models.Index(fields=["medicine", "verification_status"]),
        ]

    def __str__(self):
        return f"{self.medicine} -> {self.candidate_medicine} ({self.confidence_score:.0%}, {self.verification_status})"
