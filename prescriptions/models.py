import uuid

from django.conf import settings
from django.db import models

from medicines.models import Medicine
from .storage import private_prescription_storage


def prescription_upload_path(instance, filename):
    """Randomized filename so raw file paths aren't guessable/enumerable."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"{settings.PRESCRIPTION_UPLOAD_SUBDIR}/{instance.user_id}/{uuid.uuid4().hex}.{ext}"


class Prescription(models.Model):
    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="prescriptions")
    uploaded_file = models.FileField(
        upload_to=prescription_upload_path,
        storage=private_prescription_storage,
    )
    extracted_text = models.TextField(blank=True, help_text="Raw OCR output. Never included in application logs.")
    processing_error = models.TextField(
        blank=True,
        help_text="Human-readable processing failure reason (e.g. OCR unavailable).",
    )
    processing_status = models.CharField(
        max_length=20, choices=ProcessingStatus.choices, default=ProcessingStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "created_at"])]

    def __str__(self):
        return f"Prescription #{self.pk} — {self.user} [{self.processing_status}]"


class PrescriptionMedicine(models.Model):
    """One OCR-detected medicine line item within a prescription, pending
    (and then recording) explicit user confirmation before it is used in any
    search — OCR results are never trusted automatically (see Section 10)."""

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="detected_medicines")
    class ConfirmationStatus(models.TextChoices):
        PENDING = "pending", "Pending Review"
        CONFIRMED = "confirmed", "Confirmed"
        REJECTED = "rejected", "Rejected"

    medicine = models.ForeignKey(
        Medicine, on_delete=models.SET_NULL, null=True, blank=True, related_name="prescription_mentions"
    )
    extracted_name = models.CharField(max_length=255)
    extracted_strength = models.CharField(max_length=50, blank=True)
    match_confidence = models.FloatField(default=0.0, help_text="0.0–1.0 fuzzy-match confidence to `medicine`.")
    user_confirmed = models.BooleanField(default=False)
    confirmation_status = models.CharField(
        max_length=20, choices=ConfirmationStatus.choices, default=ConfirmationStatus.PENDING
    )

    class Meta:
        indexes = [models.Index(fields=["prescription"])]

    def __str__(self):
        return f"{self.extracted_name} ({self.extracted_strength}) -> {self.medicine or 'unmatched'}"
