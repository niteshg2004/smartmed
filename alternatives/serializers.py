from __future__ import annotations

from rest_framework import serializers

from medicines.models import Medicine
from medicines.serializers import MedicineSerializer

from .models import AlternativeCandidate


class AlternativeCandidateSerializer(serializers.ModelSerializer):
    medicine = MedicineSerializer(read_only=True)
    candidate_medicine = MedicineSerializer(read_only=True)
    similarity_score = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()
    matching_basis_display = serializers.CharField(source="get_matching_basis_display", read_only=True)
    warning = serializers.SerializerMethodField()

    class Meta:
        model = AlternativeCandidate
        fields = [
            "id",
            "medicine",
            "candidate_medicine",
            "similarity_score",
            "matching_basis",
            "matching_basis_display",
            "verification_status",
            "verified_by_name",
            "verified_at",
            "created_at",
            "warning",
        ]

    def get_similarity_score(self, obj):
        return round(float(obj.confidence_score) * 100.0, 1)

    def get_verified_by_name(self, obj):
        return obj.verified_by.name if obj.verified_by else ""

    def get_warning(self, obj):
        return (
            "Potential alternative candidate detected based on structured medicine information. "
            "Consult a qualified doctor or pharmacist before substitution."
        )


class AlternativeVerificationSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])


class AlternativeCandidateGenerateSerializer(serializers.Serializer):
    medicine_id = serializers.IntegerField(min_value=1)

    def validate_medicine_id(self, value):
        if not Medicine.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Selected medicine does not exist.")
        return value
