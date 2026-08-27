from rest_framework import serializers

from .models import Medicine, SearchHistory


class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = [
            "id", "brand_name", "generic_name", "composition", "strength",
            "dosage_form", "manufacturer", "therapeutic_category",
            "prescription_required", "description", "is_demo_data",
        ]
        read_only_fields = fields


class MedicineSearchResultSerializer(serializers.Serializer):
    medicine = MedicineSerializer()
    confidence = serializers.FloatField(help_text="0-100 fuzzy-match confidence score.")
    matched_on = serializers.ChoiceField(choices=["brand_name", "generic_name", "composition"])


class SearchHistorySerializer(serializers.ModelSerializer):
    medicine = MedicineSerializer(read_only=True)

    class Meta:
        model = SearchHistory
        fields = ["id", "medicine", "query_text", "location_text", "latitude", "longitude", "timestamp"]
        read_only_fields = fields
