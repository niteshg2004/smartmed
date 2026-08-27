from __future__ import annotations

from rest_framework import serializers

from medicines.models import Medicine
from medicines.serializers import MedicineSerializer

from .forms import PrescriptionUploadForm
from .models import Prescription, PrescriptionMedicine
from .services import get_prescription_detected_rows


class PrescriptionUploadAPISerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        form = PrescriptionUploadForm(files={"file": value}, data={})
        form.is_valid()
        errors = form.errors.get("file")
        if errors:
            raise serializers.ValidationError(errors)
        return value


class PrescriptionMedicineChoiceSerializer(serializers.Serializer):
    medicine = MedicineSerializer()
    score = serializers.FloatField()
    label = serializers.CharField()


class ApprovedAlternativeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    medicine = MedicineSerializer(source="candidate_medicine")
    similarity_score = serializers.FloatField(source="confidence_score")
    matching_basis = serializers.CharField()
    verification_status = serializers.CharField()
    verified_by_name = serializers.CharField(allow_blank=True)
    verified_at = serializers.DateTimeField(allow_null=True)
    message = serializers.CharField()


class CandidateAlternativeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    medicine = MedicineSerializer(source="candidate_medicine")
    similarity_score = serializers.FloatField(source="confidence_score")
    matching_basis = serializers.CharField()
    verification_status = serializers.CharField()
    verified_by_name = serializers.CharField(allow_blank=True)
    verified_at = serializers.DateTimeField(allow_null=True)
    message = serializers.CharField()


class PrescriptionDetectedMedicineSerializer(serializers.ModelSerializer):
    medicine = MedicineSerializer(read_only=True)
    confidence = serializers.SerializerMethodField()
    possible_matches = serializers.SerializerMethodField()
    approved_alternatives = serializers.SerializerMethodField()
    candidate_alternatives = serializers.SerializerMethodField()

    class Meta:
        model = PrescriptionMedicine
        fields = [
            "id",
            "extracted_name",
            "extracted_strength",
            "medicine",
            "confidence",
            "user_confirmed",
            "confirmation_status",
            "possible_matches",
            "candidate_alternatives",
            "approved_alternatives",
        ]

    def get_confidence(self, obj):
        return round(float(obj.match_confidence) * 100.0, 1)

    def get_possible_matches(self, obj):
        row_map = self.context.get("row_map", {})
        row = row_map.get(obj.pk, {})
        return PrescriptionMedicineChoiceSerializer(row.get("alternatives", []), many=True).data

    def get_approved_alternatives(self, obj):
        row_map = self.context.get("row_map", {})
        row = row_map.get(obj.pk, {})
        payload = []
        for candidate in row.get("approved_alternatives", []):
            payload.append(
                {
                    "id": candidate.id,
                    "candidate_medicine": candidate.candidate_medicine,
                    "confidence_score": round(float(candidate.confidence_score) * 100.0, 1),
                    "matching_basis": candidate.get_matching_basis_display(),
                    "verification_status": candidate.verification_status,
                    "verified_by_name": candidate.verified_by.name if candidate.verified_by else "",
                    "verified_at": candidate.verified_at,
                    "message": (
                        "Potential alternative candidate detected based on structured medicine information. "
                        "Consult a qualified doctor or pharmacist before substitution."
                    ),
                }
            )
        return ApprovedAlternativeSerializer(payload, many=True).data

    def get_candidate_alternatives(self, obj):
        row_map = self.context.get("row_map", {})
        row = row_map.get(obj.pk, {})
        payload = []
        for candidate in row.get("candidates", []):
            payload.append(
                {
                    "id": candidate.id,
                    "candidate_medicine": candidate.candidate_medicine,
                    "confidence_score": round(float(candidate.confidence_score) * 100.0, 1),
                    "matching_basis": candidate.get_matching_basis_display(),
                    "verification_status": candidate.verification_status,
                    "verified_by_name": candidate.verified_by.name if candidate.verified_by else "",
                    "verified_at": candidate.verified_at,
                    "message": (
                        "Potential alternative candidate detected based on structured medicine information. "
                        "Consult a qualified doctor or pharmacist before substitution."
                    ),
                }
            )
        return CandidateAlternativeSerializer(payload, many=True).data


class PrescriptionSerializer(serializers.ModelSerializer):
    detected_medicines = serializers.SerializerMethodField()
    file_download_url = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = [
            "id",
            "processing_status",
            "processing_error",
            "extracted_text",
            "created_at",
            "file_download_url",
            "detected_medicines",
        ]
        read_only_fields = fields

    def get_file_download_url(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        return request.build_absolute_uri(f"/prescriptions/{obj.pk}/file/")

    def get_detected_medicines(self, obj):
        rows = get_prescription_detected_rows(obj)
        row_map = {row["obj"].pk: row for row in rows}
        qs = obj.detected_medicines.select_related("medicine").all()
        return PrescriptionDetectedMedicineSerializer(qs, many=True, context={"row_map": row_map}).data


class PrescriptionMedicineConfirmationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    confirmed = serializers.BooleanField()
    medicine_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_medicine_id(self, value):
        if value is None:
            return value
        if not Medicine.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Selected medicine does not exist.")
        return value


class PrescriptionConfirmationSerializer(serializers.Serializer):
    items = PrescriptionMedicineConfirmationSerializer(many=True)
