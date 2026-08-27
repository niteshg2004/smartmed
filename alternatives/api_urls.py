"""Candidate matching + pharmacist verification workflow implemented in Phase 6."""
from django.urls import path

from . import api_views

app_name = "alternatives_api"

urlpatterns = [
    path("", api_views.AlternativeCandidateListAPIView.as_view(), name="list"),
    path("verify/", api_views.AlternativeVerificationQueueAPIView.as_view(), name="verify-queue"),
    path("verify/<int:pk>/", api_views.AlternativeVerifyAPIView.as_view(), name="verify"),
]
