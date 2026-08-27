from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from medicines.models import Medicine
from pharmacies.models import Pharmacy


class Inventory(models.Model):
    """Current stock snapshot for one (pharmacy, medicine) pair. Historical
    values are never overwritten in place — every change is also appended to
    InventoryHistory (see inventory/services.py, Phase 4) so the ML module
    has a real time series to train on."""

    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        LOW_STOCK = "low_stock", "Low Stock"
        OUT_OF_STOCK = "out_of_stock", "Out of Stock"

    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name="inventory_items")
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="inventory_items")
    quantity = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    availability_status = models.CharField(
        max_length=20, choices=AvailabilityStatus.choices, default=AvailabilityStatus.OUT_OF_STOCK
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    batch_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_demo_data = models.BooleanField(default=False)

    class Meta:
        ordering = ["-last_updated"]
        verbose_name_plural = "Inventory"
        constraints = [
            models.UniqueConstraint(fields=["pharmacy", "medicine"], name="unique_pharmacy_medicine_inventory")
        ]
        indexes = [
            models.Index(fields=["pharmacy", "medicine"]),
            models.Index(fields=["availability_status"]),
            models.Index(fields=["last_updated"]),
        ]

    def __str__(self):
        return f"{self.medicine} @ {self.pharmacy} = {self.quantity}"

    def derive_status(self, low_stock_threshold: int = 5) -> str:
        if self.quantity <= 0:
            return self.AvailabilityStatus.OUT_OF_STOCK
        if self.quantity <= low_stock_threshold:
            return self.AvailabilityStatus.LOW_STOCK
        return self.AvailabilityStatus.AVAILABLE

    def save(self, *args, **kwargs):
        self.availability_status = self.derive_status()
        super().save(*args, **kwargs)


class InventoryHistory(models.Model):
    """Append-only log used as the ML training signal (Phase 5) and for
    availability-confidence recency calculations (Phase 4)."""

    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name="inventory_history")
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="inventory_history")
    quantity = models.PositiveIntegerField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_demo_data = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "Inventory history"
        indexes = [
            models.Index(fields=["pharmacy", "medicine", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.medicine} @ {self.pharmacy}: {self.quantity} ({self.timestamp:%Y-%m-%d %H:%M})"


class AvailabilityRequest(models.Model):
    """A patient's explicit ping to a pharmacy asking them to confirm stock —
    distinct from the passively-observed Inventory record."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        # Legacy values kept for backward compatibility with earlier API/tests.
        CONFIRMED = "confirmed", "Confirmed"
        DENIED = "denied", "Denied"
        # Preferred patient-visible statuses.
        AVAILABLE = "available", "Available"
        LOW_STOCK = "low_stock", "Low Stock"
        OUT_OF_STOCK = "out_of_stock", "Out of Stock"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="availability_requests"
    )
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name="availability_requests")
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="availability_requests")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["pharmacy", "status"])]

    def __str__(self):
        return f"Request: {self.medicine} @ {self.pharmacy} [{self.status}]"
