from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Prescription
from .serializers import (
    PrescriptionConfirmationSerializer,
    PrescriptionDetectedMedicineSerializer,
    PrescriptionSerializer,
    PrescriptionUploadAPISerializer,
)
from .services import get_prescription_detected_rows, process_prescription, save_prescription_confirmations


def _get_prescription_for_user_or_404(*, request, pk: int) -> Prescription:
    queryset = Prescription.objects.all()
    if not request.user.is_admin_role:
        queryset = queryset.filter(user=request.user)
    return get_object_or_404(queryset, pk=pk)


class PrescriptionListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Prescription.objects.filter(user=self.request.user).order_by("-created_at")
        if self.request.user.is_admin_role:
            queryset = Prescription.objects.all().order_by("-created_at")
        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PrescriptionUploadAPISerializer
        return PrescriptionSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = PrescriptionSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prescription = Prescription.objects.create(
            user=request.user,
            uploaded_file=serializer.validated_data["file"],
        )
        process_prescription(prescription)
        output = PrescriptionSerializer(prescription, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class PrescriptionDetailAPIView(generics.RetrieveAPIView):
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Prescription.objects.all().order_by("-created_at")
        if not self.request.user.is_admin_role:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.processing_status == Prescription.ProcessingStatus.PENDING:
            process_prescription(instance)
        serializer = self.get_serializer(instance, context={"request": request})
        return Response(serializer.data)


class PrescriptionConfirmAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        prescription = _get_prescription_for_user_or_404(request=request, pk=pk)

        serializer = PrescriptionConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        allowed_ids = set(prescription.detected_medicines.values_list("pk", flat=True))
        selections = {
            item["id"]: {
                "confirmed": item["confirmed"],
                "medicine_id": item.get("medicine_id"),
            }
            for item in serializer.validated_data["items"]
        }
        unknown_ids = set(selections) - allowed_ids
        if unknown_ids:
            return Response(
                {"detail": "One or more medicine rows do not belong to this prescription."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        save_prescription_confirmations(prescription, selections)
        output = PrescriptionSerializer(prescription, context={"request": request})
        return Response(output.data)


class PrescriptionOCRAPIView(APIView):
    """
    GET /api/v1/prescriptions/<id>/ocr/

    Returns the OCR status + extracted text (if available) without the rest of
    the prescription payload.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk: int):
        prescription = _get_prescription_for_user_or_404(request=request, pk=pk)
        if prescription.processing_status == Prescription.ProcessingStatus.PENDING:
            process_prescription(prescription)
            prescription.refresh_from_db()
        return Response(
            {
                "id": prescription.id,
                "processing_status": prescription.processing_status,
                "processing_error": prescription.processing_error,
                "extracted_text": prescription.extracted_text,
            }
        )


class PrescriptionMedicinesAPIView(APIView):
    """
    GET /api/v1/prescriptions/<id>/medicines/

    Returns the OCR-detected medicine rows (and candidate matches).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk: int):
        prescription = _get_prescription_for_user_or_404(request=request, pk=pk)
        if prescription.processing_status == Prescription.ProcessingStatus.PENDING:
            process_prescription(prescription)
            prescription.refresh_from_db()

        rows = get_prescription_detected_rows(prescription)
        row_map = {row["obj"].pk: row for row in rows}
        qs = prescription.detected_medicines.select_related("medicine").all()
        return Response(
            PrescriptionDetectedMedicineSerializer(qs, many=True, context={"row_map": row_map}).data
        )
