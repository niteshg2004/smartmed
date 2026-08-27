from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from medicines.models import Medicine

from .models import AlternativeCandidate
from .serializers import (
    AlternativeCandidateGenerateSerializer,
    AlternativeCandidateSerializer,
    AlternativeVerificationSerializer,
)
from .services import review_alternative_candidate, sync_alternative_candidates_for_medicine


class AlternativeCandidateListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = AlternativeCandidateGenerateSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        medicine = get_object_or_404(Medicine, pk=serializer.validated_data["medicine_id"])
        sync_alternative_candidates_for_medicine(medicine, limit=5)
        queryset = (
            AlternativeCandidate.objects.filter(medicine=medicine)
            .select_related("medicine", "candidate_medicine", "verified_by")
            .order_by("-confidence_score")
        )
        if not request.user.is_admin_role:
            queryset = queryset.exclude(verification_status=AlternativeCandidate.VerificationStatus.REJECTED)
        output = AlternativeCandidateSerializer(queryset, many=True)
        return Response(output.data)


class AlternativeVerificationQueueAPIView(generics.ListAPIView):
    serializer_class = AlternativeCandidateSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get_queryset(self):
        queryset = (
            AlternativeCandidate.objects.select_related("medicine", "candidate_medicine", "verified_by")
            .order_by("-confidence_score")
        )
        status_filter = self.request.query_params.get("status", AlternativeCandidate.VerificationStatus.PENDING)
        if status_filter:
            queryset = queryset.filter(verification_status=status_filter)
        return queryset


class AlternativeVerifyAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request, pk: int):
        candidate = get_object_or_404(
            AlternativeCandidate.objects.select_related("medicine", "candidate_medicine", "verified_by"),
            pk=pk,
        )
        serializer = AlternativeVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approve = serializer.validated_data["action"] == "approve"
        review_alternative_candidate(candidate, user=request.user, approve=approve)
        return Response(AlternativeCandidateSerializer(candidate).data, status=status.HTTP_200_OK)
