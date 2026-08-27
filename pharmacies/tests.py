from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from inventory.models import Inventory, InventoryHistory
from medicines.models import Medicine

from .models import Pharmacy
from .services import haversine_km


class NearbyPharmacyTests(TestCase):
    def test_haversine_distance_is_zero_for_same_point(self):
        self.assertEqual(haversine_km(18.52, 73.86, 18.52, 73.86), 0.0)


class NearbyPharmacyAPITests(APITestCase):
    def setUp(self):
        owner = User.objects.create_user(
            email="nearby-owner@example.com",
            password="StrongPass123",
            name="Nearby Owner",
            role=User.Role.PHARMACY,
        )
        self.medicine = Medicine.objects.create(
            brand_name="Dolo 650",
            generic_name="Paracetamol",
            composition="Paracetamol",
            strength="650mg",
            dosage_form=Medicine.DosageForm.TABLET,
            manufacturer="Micro Labs",
            therapeutic_category="Analgesic / Antipyretic",
            is_demo_data=True,
        )
        self.nearby = Pharmacy.objects.create(
            owner=owner,
            name="Nearby Pharmacy",
            address="Near Road",
            latitude=18.5205,
            longitude=73.8605,
            verification_status=Pharmacy.VerificationStatus.VERIFIED,
            is_demo_data=True,
        )
        self.far = Pharmacy.objects.create(
            owner=owner,
            name="Far Pharmacy",
            address="Far Road",
            latitude=19.10,
            longitude=74.20,
            verification_status=Pharmacy.VerificationStatus.VERIFIED,
            is_demo_data=True,
        )
        Inventory.objects.create(
            pharmacy=self.nearby,
            medicine=self.medicine,
            quantity=28,
            is_demo_data=True,
        )
        InventoryHistory.objects.create(
            pharmacy=self.nearby,
            medicine=self.medicine,
            quantity=25,
            timestamp=timezone.now() - timedelta(days=1),
            is_demo_data=True,
        )

    def test_nearby_api_returns_only_pharmacies_within_radius(self):
        response = self.client.get(
            reverse("pharmacies_api:pharmacy-nearby"),
            {"lat": 18.52, "lng": 73.86, "radius_km": 5, "medicine_id": self.medicine.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Nearby Pharmacy")
        self.assertIn("availability", response.data["results"][0])
