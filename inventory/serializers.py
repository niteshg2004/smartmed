from rest_framework import serializers

from .models import AvailabilityRequest, Inventory, InventoryHistory

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'

class InventoryHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryHistory
        fields = '__all__'

class AvailabilityRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilityRequest
        fields = "__all__"
        read_only_fields = ["user", "created_at", "updated_at"]


class AvailabilityRequestRespondSerializer(serializers.ModelSerializer):
    """Used by pharmacy/admin to respond to a request."""

    class Meta:
        model = AvailabilityRequest
        fields = ["status", "response"]

class InventoryUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    batch_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    expiry_date = serializers.DateField(required=False)
