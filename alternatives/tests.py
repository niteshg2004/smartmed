from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from accounts.models import User
from medicines.models import Medicine

from .models import AlternativeCandidate
from .services import sync_alternative_candidates_for_medicine


class AlternativeVerificationAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin-alt@example.com",
            password="StrongPass123",
            name="Admin",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.patient = User.objects.create_user(
            email="patient-alt@example.com",
            password="StrongPass123",
            name="Patient",
            role=User.Role.PATIENT,
        )

        self.source = Medicine.objects.create(
            brand_name="Dolo 650",
            generic_name="Paracetamol",
            composition="Paracetamol",
            strength="650mg",
            dosage_form=Medicine.DosageForm.TABLET,
            manufacturer="Micro Labs",
        )
        self.cand = Medicine.objects.create(
            brand_name="Paracetamol 650",
            generic_name="Paracetamol",
            composition="Paracetamol",
            strength="650mg",
            dosage_form=Medicine.DosageForm.TABLET,
            manufacturer="Some Pharma",
        )

        sync_alternative_candidates_for_medicine(self.source, limit=5)
        self.candidate_obj = AlternativeCandidate.objects.filter(medicine=self.source).first()

    def test_patient_cannot_verify_candidate(self):
        self.client.force_authenticate(user=self.patient)
        resp = self.client.post(
            reverse("alternatives_api:verify", args=[self.candidate_obj.id]),
            {"action": "approve"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_approve_candidate(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            reverse("alternatives_api:verify", args=[self.candidate_obj.id]),
            {"action": "approve"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.candidate_obj.refresh_from_db()
        self.assertEqual(self.candidate_obj.verification_status, AlternativeCandidate.VerificationStatus.APPROVED)
        self.assertEqual(self.candidate_obj.verified_by_id, self.admin.id)

