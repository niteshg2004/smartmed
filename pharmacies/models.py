from django.conf import settings
from django.db import models


class Pharmacy(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pharmacies",
        limit_choices_to={"role": "pharmacy"},
        help_text="The pharmacy-role user account that manages this pharmacy.",
    )
    name = models.CharField(max_length=200, db_index=True)
    address = models.CharField(max_length=400)
    latitude = models.FloatField()
    longitude = models.FloatField()
    phone = models.CharField(max_length=20, blank=True)
    opening_hours = models.JSONField(
        default=dict,
        blank=True,
        help_text='e.g. {"mon": ["09:00", "21:00"], "sun": null}',
    )
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )
    is_demo_data = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Pharmacies"
        indexes = [
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["verification_status"]),
        ]

    def __str__(self):
        return self.name

    @property
    def is_verified(self):
        return self.verification_status == self.VerificationStatus.VERIFIED
