from django.db.models import Prefetch
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsOwnerPharmacyOrAdmin, IsPharmacyRole
from inventory.availability import compute_availability
from inventory.models import Inventory, InventoryHistory
from medicines.models import Medicine

from .models import Pharmacy
from .serializers import PharmacyListSerializer, PharmacySerializer
from .services import haversine_km, parse_float

class PharmacyListCreateAPIView(generics.ListCreateAPIView):
    queryset = Pharmacy.objects.all()
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return PharmacyListSerializer
        return PharmacySerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsPharmacyRole()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class PharmacyDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Pharmacy.objects.all()
    serializer_class = PharmacySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerPharmacyOrAdmin]


class NearbyPharmaciesAPIView(APIView):
    """
    GET /api/v1/pharmacies/nearby/?lat=18.52&lng=73.85&radius_km=5&medicine_id=123

    Returns nearby verified pharmacies (demo-friendly, no paid APIs) with
    distance, and (optionally) availability-confidence for a specific
    medicine.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        lat = parse_float(request.query_params.get("lat"))
        lng = parse_float(request.query_params.get("lng"))
        if lat is None or lng is None:
            raise ValidationError({"lat": "lat is required", "lng": "lng is required"})

        try:
            radius_km = float(request.query_params.get("radius_km", "5"))
        except ValueError:
            raise ValidationError({"radius_km": "radius_km must be a number"})
        radius_km = max(0.5, min(radius_km, 50.0))

        medicine_id = request.query_params.get("medicine_id")
        medicine = None
        if medicine_id:
            try:
                medicine = Medicine.objects.get(pk=int(medicine_id))
            except (ValueError, Medicine.DoesNotExist):
                raise ValidationError({"medicine_id": "Invalid medicine_id"})

        pharmacies_qs = Pharmacy.objects.filter(
            verification_status=Pharmacy.VerificationStatus.VERIFIED
        ).order_by("name")

        pharmacies = list(pharmacies_qs)
        if not pharmacies:
            return Response({"count": 0, "results": []})

        inv_by_pharmacy = {}
        history_by_pharmacy = {}
        if medicine is not None:
            inv_qs = (
                Inventory.objects.filter(medicine=medicine, pharmacy__in=pharmacies)
                .select_related("pharmacy", "medicine")
                .only(
                    "id",
                    "pharmacy_id",
                    "medicine_id",
                    "quantity",
                    "last_updated",
                    "availability_status",
                    "is_demo_data",
                )
            )
            inv_by_pharmacy = {i.pharmacy_id: i for i in inv_qs}

            hist_qs = InventoryHistory.objects.filter(
                medicine=medicine, pharmacy__in=pharmacies
            ).order_by("-timestamp")
            # Group in python; demo dataset is small (10 pharmacies).
            for h in hist_qs[:2000]:
                history_by_pharmacy.setdefault(h.pharmacy_id, []).append(h)

        results = []
        for p in pharmacies:
            d = haversine_km(lat, lng, p.latitude, p.longitude)
            if d > radius_km:
                continue

            payload = {
                "id": p.id,
                "name": p.name,
                "address": p.address,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "phone": p.phone,
                "verification_status": p.verification_status,
                "distance_km": round(d, 2),
                "is_demo_data": p.is_demo_data,
            }

            if medicine is not None:
                inv = inv_by_pharmacy.get(p.id)
                availability = compute_availability(
                    pharmacy=p,
                    inventory=inv,
                    recent_history_qs=history_by_pharmacy.get(p.id, []),
                )
                payload["availability"] = {
                    "availability_status": availability.availability_status,
                    "confidence_score": availability.confidence_score,
                    "explanation": availability.explanation,
                    "last_updated": availability.last_updated,
                    "stock": (inv.quantity if inv else None),
                }

            results.append(payload)

        results.sort(key=lambda r: r["distance_km"])
        return Response({"count": len(results), "results": results})
