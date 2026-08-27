from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from medicines.models import Medicine
from pharmacies.models import Pharmacy

from .availability import compute_availability
from .models import AvailabilityRequest, Inventory, InventoryHistory
from .services import update_inventory


class InventoryTestDataMixin:
    def create_base_data(self):
        pharmacy_user = User.objects.create_user(
            email="pharmacy@example.com",
            password="StrongPass123",
            name="Pharmacy User",
            role=User.Role.PHARMACY,
        )
        other_pharmacy_user = User.objects.create_user(
            email="other-pharmacy@example.com",
            password="StrongPass123",
            name="Other Pharmacy User",
            role=User.Role.PHARMACY,
        )
        patient = User.objects.create_user(
            email="patient-inventory@example.com",
            password="StrongPass123",
            name="Patient User",
            role=User.Role.PATIENT,
        )
        pharmacy = Pharmacy.objects.create(
            owner=pharmacy_user,
            name="Verified Pharmacy",
            address="Main Road",
            latitude=18.52,
            longitude=73.86,
            verification_status=Pharmacy.VerificationStatus.VERIFIED,
            is_demo_data=True,
        )
        other_pharmacy = Pharmacy.objects.create(
            owner=other_pharmacy_user,
            name="Other Pharmacy",
            address="Side Road",
            latitude=18.55,
            longitude=73.80,
            verification_status=Pharmacy.VerificationStatus.VERIFIED,
            is_demo_data=True,
        )
        medicine = Medicine.objects.create(
            brand_name="Dolo 650",
            generic_name="Paracetamol",
            composition="Paracetamol",
            strength="650mg",
            dosage_form=Medicine.DosageForm.TABLET,
            manufacturer="Micro Labs",
            therapeutic_category="Analgesic / Antipyretic",
            is_demo_data=True,
        )
        return pharmacy_user, other_pharmacy_user, patient, pharmacy, other_pharmacy, medicine


class AvailabilityScoringTests(InventoryTestDataMixin, TestCase):
    def setUp(self):
        (
            self.pharmacy_user,
            self.other_pharmacy_user,
            self.patient,
            self.pharmacy,
            self.other_pharmacy,
            self.medicine,
        ) = self.create_base_data()

    def test_compute_availability_returns_available_for_recent_stock(self):
        inventory = Inventory.objects.create(
            pharmacy=self.pharmacy,
            medicine=self.medicine,
            quantity=25,
            is_demo_data=True,
        )
        for days_ago, qty in [(3, 24), (2, 22), (1, 20)]:
            InventoryHistory.objects.create(
                pharmacy=self.pharmacy,
                medicine=self.medicine,
                quantity=qty,
                timestamp=timezone.now() - timedelta(days=days_ago),
                is_demo_data=True,
            )

        result = compute_availability(pharmacy=self.pharmacy, inventory=inventory)
        self.assertEqual(result.availability_status, "AVAILABLE")
        self.assertGreaterEqual(result.confidence_score, 70)

    def test_compute_availability_flags_stale_data(self):
        inventory = Inventory.objects.create(
            pharmacy=self.pharmacy,
            medicine=self.medicine,
            quantity=10,
            is_demo_data=True,
        )
        Inventory.objects.filter(pk=inventory.pk).update(last_updated=timezone.now() - timedelta(days=10))
        inventory.refresh_from_db()

        result = compute_availability(pharmacy=self.pharmacy, inventory=inventory)
        self.assertEqual(result.availability_status, "STALE DATA")
        self.assertLess(result.confidence_score, 50)


class InventoryHistoryServiceTests(InventoryTestDataMixin, TestCase):
    def setUp(self):
        (
            self.pharmacy_user,
            self.other_pharmacy_user,
            self.patient,
            self.pharmacy,
            self.other_pharmacy,
            self.medicine,
        ) = self.create_base_data()

    def test_update_inventory_creates_history_record(self):
        inventory = update_inventory(
            pharmacy=self.pharmacy,
            medicine=self.medicine,
            quantity=30,
        )
        self.assertEqual(inventory.quantity, 30)
        self.assertEqual(InventoryHistory.objects.count(), 1)
        self.assertEqual(InventoryHistory.objects.first().quantity, 30)


class AvailabilityRequestAPITests(InventoryTestDataMixin, APITestCase):
    def setUp(self):
        (
            self.pharmacy_user,
            self.other_pharmacy_user,
            self.patient,
            self.pharmacy,
            self.other_pharmacy,
            self.medicine,
        ) = self.create_base_data()
        self.request = AvailabilityRequest.objects.create(
            user=self.patient,
            pharmacy=self.pharmacy,
            medicine=self.medicine,
        )

    def test_patient_can_create_request(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(
            reverse("inventory_api:request-create"),
            {"pharmacy": self.pharmacy.id, "medicine": self.medicine.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AvailabilityRequest.objects.filter(user=self.patient).count(), 2)

    def test_pharmacy_owner_can_respond_to_own_request(self):
        self.client.force_authenticate(user=self.pharmacy_user)
        response = self.client.patch(
            reverse("inventory_api:request-respond", args=[self.request.id]),
            {"status": "confirmed", "response": "Available now"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, "confirmed")

    def test_other_pharmacy_owner_cannot_respond(self):
        self.client.force_authenticate(user=self.other_pharmacy_user)
        response = self.client.patch(
            reverse("inventory_api:request-respond", args=[self.request.id]),
            {"status": "denied", "response": "Out of stock"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
