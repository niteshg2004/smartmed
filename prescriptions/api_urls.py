"""Prescription upload + OCR pipeline endpoints implemented in Phase 7."""
from django.urls import path

from . import api_views

app_name = "prescriptions_api"

urlpatterns = [
    path("", api_views.PrescriptionListCreateAPIView.as_view(), name="list-create"),
    path("<int:pk>/", api_views.PrescriptionDetailAPIView.as_view(), name="detail"),
    path("<int:pk>/ocr/", api_views.PrescriptionOCRAPIView.as_view(), name="ocr"),
    path("<int:pk>/medicines/", api_views.PrescriptionMedicinesAPIView.as_view(), name="medicines"),
    path("<int:pk>/confirm/", api_views.PrescriptionConfirmAPIView.as_view(), name="confirm"),
]
