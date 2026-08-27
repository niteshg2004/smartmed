from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional

from django.utils import timezone

from pharmacies.models import Pharmacy

from .models import Inventory, InventoryHistory


@dataclass(frozen=True)
class AvailabilityResult:
    availability_status: str
    confidence_score: int  # 0-100
    explanation: List[str]
    last_updated: Optional[timezone.datetime]


def _clamp(n: float, lo: int = 0, hi: int = 100) -> int:
    return int(max(lo, min(hi, round(n))))


def compute_availability(
    *,
    pharmacy: Pharmacy,
    inventory: Optional[Inventory],
    recent_history_qs=None,
    now=None,
    low_stock_threshold: int = 5,
    stale_after_days: int = 7,
) -> AvailabilityResult:
    """
    Explainable availability-confidence scoring.

    This is a *decision-support* signal, not a guarantee of live inventory:
    it combines current stock snapshot, recency, pharmacy verification, and
    recent history patterns (stock-outs / low-stock frequency).
    """
    now = now or timezone.now()

    if inventory is None:
        return AvailabilityResult(
            availability_status="UNKNOWN",
            confidence_score=20,
            explanation=[
                "No inventory record found for this pharmacy and medicine.",
                "Availability is unknown. Please contact the pharmacy before visiting.",
            ],
            last_updated=None,
        )

    # ------------------------------------------------------------------
    # Base status from quantity
    # ------------------------------------------------------------------
    qty = inventory.quantity or 0
    if qty <= 0:
        status = "OUT OF STOCK"
        base_conf = 85
    elif qty <= low_stock_threshold:
        status = "LOW STOCK"
        base_conf = 75
    else:
        status = "AVAILABLE"
        base_conf = 80

    # ------------------------------------------------------------------
    # Recency adjustment (stale data handling)
    # ------------------------------------------------------------------
    last_updated = inventory.last_updated
    age = (now - last_updated) if last_updated else timedelta(days=9999)

    if age > timedelta(days=stale_after_days):
        # Stale data: we deliberately avoid claiming availability.
        return AvailabilityResult(
            availability_status="STALE DATA",
            confidence_score=39,
            explanation=[
                f"Inventory data may be outdated (last update {age.days} day(s) ago).",
                "Please contact the pharmacy to confirm before visiting.",
            ],
            last_updated=last_updated,
        )

    recency_adj = 0
    if age <= timedelta(minutes=15):
        recency_adj = +12
    elif age <= timedelta(hours=1):
        recency_adj = +8
    elif age <= timedelta(hours=24):
        recency_adj = 0
    elif age <= timedelta(days=3):
        recency_adj = -12
    else:
        recency_adj = -22

    # ------------------------------------------------------------------
    # Pharmacy verification adjustment
    # ------------------------------------------------------------------
    verification_adj = 0
    if not pharmacy.is_verified:
        verification_adj = -10

    # ------------------------------------------------------------------
    # History adjustment: penalize availability confidence if the last ~14d
    # frequently dips to 0/low (volatile / frequent stock-outs).
    # ------------------------------------------------------------------
    history_adj = 0
    if recent_history_qs is None:
        recent_history_qs = InventoryHistory.objects.filter(
            pharmacy=pharmacy, medicine=inventory.medicine, timestamp__gte=now - timedelta(days=14)
        ).only("quantity", "timestamp")

    history = list(recent_history_qs[:200])  # guardrails
    if history:
        low_days = sum(1 for h in history if (h.quantity or 0) <= low_stock_threshold)
        out_days = sum(1 for h in history if (h.quantity or 0) <= 0)
        ratio_low = low_days / max(1, len(history))

        # If we're claiming AVAILABLE but history is often low/out, reduce confidence.
        if status == "AVAILABLE":
            if ratio_low >= 0.5:
                history_adj = -20
            elif ratio_low >= 0.25:
                history_adj = -12
            elif ratio_low >= 0.10:
                history_adj = -6

        # If we're claiming OUT OF STOCK but stock-outs are very rare, reduce a little.
        if status == "OUT OF STOCK" and out_days <= 1:
            history_adj = -8

    conf = _clamp(base_conf + recency_adj + verification_adj + history_adj)

    explanation = [
        f"Current stock: {qty}",
        f"Last updated: {int(age.total_seconds() // 60)} minute(s) ago",
    ]
    if not pharmacy.is_verified:
        explanation.append("Pharmacy verification status: pending/unverified (confidence reduced).")
    if history_adj < 0 and status == "AVAILABLE":
        explanation.append("Recent history shows frequent low-stock/stock-outs (confidence reduced).")

    return AvailabilityResult(
        availability_status=status,
        confidence_score=conf,
        explanation=explanation,
        last_updated=last_updated,
    )

