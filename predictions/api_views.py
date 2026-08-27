from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import Inventory
from ml.predict import predict_stock


class PredictionRequestSerializer(serializers.Serializer):
    pharmacy_id = serializers.IntegerField(min_value=1)
    medicine_id = serializers.IntegerField(min_value=1)
    horizon_days = serializers.IntegerField(min_value=1, max_value=30, default=7)


class PredictionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = PredictionRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        pharmacy_id = serializer.validated_data["pharmacy_id"]
        medicine_id = serializer.validated_data["medicine_id"]
        horizon_days = serializer.validated_data["horizon_days"]

        inventory = (
            Inventory.objects.filter(pharmacy_id=pharmacy_id, medicine_id=medicine_id)
            .select_related("pharmacy", "medicine")
            .first()
        )
        if inventory is None:
            return Response(
                {"detail": "Inventory record not found for the selected pharmacy and medicine."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            result = predict_stock(
                pharmacy_id=pharmacy_id,
                medicine_id=medicine_id,
                horizon_days=horizon_days,
            )
        except FileNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(
            {
                "pharmacy": {
                    "id": inventory.pharmacy_id,
                    "name": inventory.pharmacy.name,
                    "is_demo_data": inventory.pharmacy.is_demo_data,
                },
                "medicine": {
                    "id": inventory.medicine_id,
                    "brand_name": inventory.medicine.brand_name,
                    "generic_name": inventory.medicine.generic_name,
                    "strength": inventory.medicine.strength,
                    "is_demo_data": inventory.medicine.is_demo_data,
                },
                "current_stock": inventory.quantity,
                "predicted_next_day_demand": result.predicted_demand,
                "average_daily_demand_7d": result.avg_daily_demand_7d,
                "predicted_remaining_stock": result.predicted_remaining_stock,
                "stockout_probability": result.stockout_probability,
                "predicted_stockout_date": result.predicted_stockout_date,
                "risk_level": result.risk,
                "horizon_days": horizon_days,
                "is_demo_data": bool(inventory.is_demo_data or inventory.medicine.is_demo_data),
                "model_info": result.model_info,
            }
        )
