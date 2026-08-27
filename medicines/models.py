import re

from django.conf import settings
from django.db import models


def normalize_text(value: str) -> str:
    """Lowercase, strip punctuation/extra whitespace — used for fast exact/prefix
    lookups; fuzzy matching (RapidFuzz, Phase 2) works off this normalized field
    too, since it removes noise that would otherwise hurt match scores."""
    if not value:
        return ""
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


class Medicine(models.Model):
    class DosageForm(models.TextChoices):
        TABLET = "tablet", "Tablet"
        CAPSULE = "capsule", "Capsule"
        SYRUP = "syrup", "Syrup"
        INJECTION = "injection", "Injection"
        CREAM = "cream", "Cream/Ointment"
        DROPS = "drops", "Drops"
        INHALER = "inhaler", "Inhaler"
        OTHER = "other", "Other"

    brand_name = models.CharField(max_length=200, db_index=True)
    generic_name = models.CharField(max_length=200, db_index=True)
    composition = models.CharField(
        max_length=300,
        help_text="Active ingredient(s), e.g. 'Paracetamol' or 'Amoxicillin + Clavulanic Acid'.",
    )
    strength = models.CharField(max_length=50, help_text="e.g. '650mg', '500mg/5ml'")
    dosage_form = models.CharField(max_length=20, choices=DosageForm.choices, default=DosageForm.TABLET)
    manufacturer = models.CharField(max_length=200, blank=True)
    therapeutic_category = models.CharField(max_length=150, blank=True, db_index=True)
    prescription_required = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    # Precomputed normalized field for fast search; kept in sync in save().
    normalized_search_key = models.CharField(max_length=500, db_index=True, editable=False, blank=True)

    is_demo_data = models.BooleanField(
        default=False,
        help_text="True if seeded by the demo data generator rather than a real import.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["brand_name"]
        indexes = [
            models.Index(fields=["brand_name"]),
            models.Index(fields=["generic_name"]),
            models.Index(fields=["therapeutic_category"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["brand_name", "strength", "manufacturer"],
                name="unique_medicine_brand_strength_manufacturer",
            )
        ]

    def __str__(self):
        return f"{self.brand_name} {self.strength}"

    def save(self, *args, **kwargs):
        self.normalized_search_key = normalize_text(
            f"{self.brand_name} {self.generic_name} {self.composition} {self.strength}"
        )
        super().save(*args, **kwargs)


class SearchHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_history"
    )
    medicine = models.ForeignKey(
        Medicine, on_delete=models.SET_NULL, null=True, blank=True, related_name="search_events"
    )
    query_text = models.CharField(max_length=200, help_text="Raw text the user typed.")
    location_text = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["medicine", "timestamp"]),
            models.Index(fields=["user", "timestamp"]),
        ]
        verbose_name_plural = "Search history"

    def __str__(self):
        return f"{self.user} searched '{self.query_text}' @ {self.timestamp:%Y-%m-%d %H:%M}"
