from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import AlternativeCandidate
from .services import review_alternative_candidate


@login_required
@permission_required("accounts.can_verify_alternatives", raise_exception=True)
@require_http_methods(["GET", "POST"])
def verification_queue_view(request):
    if request.method == "POST":
        candidate = get_object_or_404(AlternativeCandidate, pk=request.POST.get("candidate_id"))
        action = request.POST.get("action")
        review_alternative_candidate(candidate, user=request.user, approve=action == "approve")
        messages.success(
            request,
            f"Alternative candidate {candidate.pk} marked as {candidate.get_verification_status_display().lower()}.",
        )
        return redirect("alternatives:verification-queue")

    queryset = (
        AlternativeCandidate.objects.select_related("medicine", "candidate_medicine", "verified_by")
        .order_by("verification_status", "-confidence_score")
    )
    status_filter = request.GET.get("status", AlternativeCandidate.VerificationStatus.PENDING)
    if status_filter:
        queryset = queryset.filter(verification_status=status_filter)

    return render(
        request,
        "alternatives/verification_queue.html",
        {
            "alternatives": queryset[:200],
            "status_filter": status_filter,
            "status_choices": AlternativeCandidate.VerificationStatus.choices,
        },
    )
