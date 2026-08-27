from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.models import User
from medicines.models import SearchHistory
from prescriptions.models import Prescription
from inventory.models import AvailabilityRequest, Inventory
from alternatives.models import AlternativeCandidate


@login_required
def home(request):
    """
    Routes to a role-appropriate dashboard with live data from each app's
    existing models and services.
    """
    user = request.user
    context = {"user": user}

    if user.role == User.Role.PHARMACY:
        template = "dashboard/pharmacy_home.html"
        inventory_qs = Inventory.objects.filter(pharmacy__owner=user).select_related("medicine", "pharmacy")
        context.update(
            {
                "inventory_count": inventory_qs.count(),
                "low_stock_count": inventory_qs.filter(quantity__gt=0, quantity__lte=5).count(),
                "out_of_stock_count": inventory_qs.filter(quantity__lte=0).count(),
                "recent_requests": AvailabilityRequest.objects.filter(pharmacy__owner=user)
                .select_related("medicine", "user")
                .order_by("-created_at")[:5],
            }
        )
    elif user.is_admin_role:
        template = "dashboard/admin_home.html"
        context.update(
            {
                "pending_alternatives": AlternativeCandidate.objects.filter(
                    verification_status=AlternativeCandidate.VerificationStatus.PENDING
                )
                .select_related("medicine", "candidate_medicine")
                .order_by("-confidence_score")[:8],
                "recent_availability_requests": AvailabilityRequest.objects.select_related(
                    "medicine", "pharmacy", "user"
                ).order_by("-created_at")[:8],
            }
        )
    else:
        template = "dashboard/patient_home.html"
        context.update(
            {
                "recent_searches": SearchHistory.objects.filter(user=user)
                .select_related("medicine")
                .order_by("-timestamp")[:5],
                "recent_prescriptions": Prescription.objects.filter(user=user).order_by("-created_at")[:5],
                "recent_availability_requests": AvailabilityRequest.objects.filter(user=user)
                .select_related("medicine", "pharmacy")
                .order_by("-created_at")[:5],
            }
        )

    return render(request, template, context)
