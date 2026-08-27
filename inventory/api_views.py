from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Inventory, InventoryHistory, AvailabilityRequest
from .serializers import (
    AvailabilityRequestRespondSerializer,
    AvailabilityRequestSerializer,
    InventoryHistorySerializer,
    InventorySerializer,
    InventoryUpdateSerializer,
)
from .services import update_inventory
from accounts.permissions import IsPharmacyRole, IsPatient, IsOwnerPharmacyOrAdmin
from django.shortcuts import get_object_or_404
from medicines.models import Medicine
from pharmacies.models import Pharmacy
from .availability import compute_availability

class InventoryListAPIView(generics.ListAPIView):
    serializer_class = InventorySerializer
    
    def get_queryset(self):
        queryset = Inventory.objects.all()
        pharmacy_id = self.request.query_params.get('pharmacy_id')
        medicine_id = self.request.query_params.get('medicine_id')
        
        if pharmacy_id:
            queryset = queryset.filter(pharmacy_id=pharmacy_id)
        if medicine_id:
            queryset = queryset.filter(medicine_id=medicine_id)
            
        return queryset

class InventoryUpdateAPIView(generics.CreateAPIView):
    serializer_class = InventoryUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerPharmacyOrAdmin]
    
    def post(self, request, pharmacy_id, medicine_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if request.user.role == 'admin':
            pharmacy = get_object_or_404(Pharmacy, id=pharmacy_id)
        else:
            pharmacy = get_object_or_404(Pharmacy, id=pharmacy_id, owner=request.user)
            
        medicine = get_object_or_404(Medicine, id=medicine_id)
        
        try:
            inventory = update_inventory(
                pharmacy=pharmacy,
                medicine=medicine,
                quantity=serializer.validated_data['quantity'],
                price=serializer.validated_data.get('price'),
                batch_number=serializer.validated_data.get('batch_number', ''),
                expiry_date=serializer.validated_data.get('expiry_date')
            )
            return Response(InventorySerializer(inventory).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class InventoryHistoryAPIView(generics.ListAPIView):
    serializer_class = InventoryHistorySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerPharmacyOrAdmin]
    
    def get_queryset(self):
        pharmacy_id = self.kwargs['pharmacy_id']
        medicine_id = self.kwargs['medicine_id']
        return InventoryHistory.objects.filter(pharmacy_id=pharmacy_id, medicine_id=medicine_id)

class AvailabilityRequestCreateAPIView(generics.CreateAPIView):
    serializer_class = AvailabilityRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsPatient]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class AvailabilityRequestRespondAPIView(generics.UpdateAPIView):
    queryset = AvailabilityRequest.objects.all()
    serializer_class = AvailabilityRequestRespondSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerPharmacyOrAdmin]
    
    def get_serializer(self, *args, **kwargs):
        kwargs['partial'] = True
        return super().get_serializer(*args, **kwargs)
        
    def perform_update(self, serializer):
        serializer.save()


class MyAvailabilityRequestsAPIView(generics.ListAPIView):
    """Patient: list their own requests."""

    serializer_class = AvailabilityRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def get_queryset(self):
        return (
            AvailabilityRequest.objects.filter(user=self.request.user)
            .select_related("pharmacy", "medicine")
            .order_by("-created_at")
        )


class PharmacyAvailabilityInboxAPIView(generics.ListAPIView):
    """Pharmacy: list incoming requests for their pharmacy."""

    serializer_class = AvailabilityRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsPharmacyRole]

    def get_queryset(self):
        pharmacy = get_object_or_404(Pharmacy, owner=self.request.user)
        return (
            AvailabilityRequest.objects.filter(pharmacy=pharmacy)
            .select_related("user", "medicine")
            .order_by("-created_at")
        )


class AvailabilityAPIView(generics.GenericAPIView):
    """
    GET /api/v1/inventory/availability/?pharmacy_id=1&medicine_id=2

    Returns an explainable availability status + confidence score.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        pharmacy_id = request.query_params.get("pharmacy_id")
        medicine_id = request.query_params.get("medicine_id")
        if not pharmacy_id or not medicine_id:
            return Response(
                {"detail": "pharmacy_id and medicine_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pharmacy = get_object_or_404(Pharmacy, pk=pharmacy_id)
        medicine = get_object_or_404(Medicine, pk=medicine_id)
        inventory = (
            Inventory.objects.filter(pharmacy=pharmacy, medicine=medicine)
            .select_related("pharmacy", "medicine")
            .first()
        )

        result = compute_availability(pharmacy=pharmacy, inventory=inventory)
        payload = {
            "pharmacy_id": pharmacy.id,
            "medicine_id": medicine.id,
            "availability_status": result.availability_status,
            "confidence_score": result.confidence_score,
            "explanation": result.explanation,
            "last_updated": result.last_updated,
            "stock": inventory.quantity if inventory else None,
        }
        return Response(payload)
