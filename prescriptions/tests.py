import tempfile
from pathlib import Path
from unittest.mock import patch
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from medicines.models import Medicine
from prescriptions.models import Prescription, PrescriptionMedicine
from prescriptions.ocr import OCRResult, OCRUnavailableError
from prescriptions.storage import PrivatePrescriptionStorage


class PrescriptionWorkflowTests(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

        # Keep private uploads out of the repository during tests.
        storage = PrivatePrescriptionStorage(location=Path(self.tmpdir.name) / "private_uploads")
        Prescription._meta.get_field("uploaded_file").storage = storage

        self.user = User.objects.create_user(
            email="patient@example.com",
            password="StrongPass123",
            name="Patient",
            role=User.Role.PATIENT,
        )

    def login(self):
        self.client.login(email=self.user.email, password="StrongPass123")

    def make_png_upload(self, name="rx.png"):
        try:
            from PIL import Image
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("PIL is required for prescription tests") from exc

        buf = BytesIO()
        Image.new("RGB", (10, 10), color=(255, 255, 255)).save(buf, format="PNG")
        return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")

    def test_upload_requires_login(self):
        resp = self.client.get(reverse("prescriptions:upload"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:login"), resp.url)

    def test_upload_rejects_invalid_content_type(self):
        self.login()
        upload = SimpleUploadedFile("note.txt", b"hello", content_type="text/plain")
        resp = self.client.post(reverse("prescriptions:upload"), {"file": upload})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Unsupported file type", html=False)

    @patch("prescriptions.services.ocr_file_to_text")
    def test_upload_and_ocr_detects_medicines(self, mock_ocr):
        self.login()
        Medicine.objects.create(
            brand_name="Dolo 650",
            generic_name="Paracetamol",
            composition="Paracetamol",
            strength="650mg",
            dosage_form=Medicine.DosageForm.TABLET,
            manufacturer="Micro Labs",
        )
        Medicine.objects.create(
            brand_name="Pantocid 40",
            generic_name="Pantoprazole",
            composition="Pantoprazole",
            strength="40mg",
            dosage_form=Medicine.DosageForm.TABLET,
            manufacturer="Sun Pharma",
        )

        mock_ocr.return_value = OCRResult(text="Dolo 650\nPantocid 40\nTake after food")

        upload = self.make_png_upload()
        resp = self.client.post(reverse("prescriptions:upload"), {"file": upload})
        self.assertEqual(resp.status_code, 302)

        prescription = Prescription.objects.first()
        detail_url = reverse("prescriptions:detail", kwargs={"pk": prescription.pk})
        resp2 = self.client.get(detail_url)
        self.assertEqual(resp2.status_code, 200)

        prescription.refresh_from_db()
        self.assertEqual(prescription.processing_status, Prescription.ProcessingStatus.PROCESSED)
        self.assertTrue(prescription.detected_medicines.exists())
        self.assertContains(resp2, "Dolo 650")

    @patch("prescriptions.services.ocr_file_to_text")
    def test_ocr_unavailable_is_graceful(self, mock_ocr):
        self.login()
        mock_ocr.side_effect = OCRUnavailableError("missing")

        upload = self.make_png_upload()
        resp = self.client.post(reverse("prescriptions:upload"), {"file": upload})
        self.assertEqual(resp.status_code, 302)

        prescription = Prescription.objects.first()
        resp2 = self.client.get(reverse("prescriptions:detail", kwargs={"pk": prescription.pk}))
        self.assertEqual(resp2.status_code, 200)

        prescription.refresh_from_db()
        self.assertEqual(prescription.processing_status, Prescription.ProcessingStatus.FAILED)

    def test_upload_rejects_oversized_file(self):
        self.login()
        big = b"\x00" * (6 * 1024 * 1024)  # 6MB dummy payload; will fail either size or image validation
        upload = SimpleUploadedFile("rx.png", big, content_type="image/png")
        resp = self.client.post(reverse("prescriptions:upload"), {"file": upload})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "File too large", html=False)

    @patch("prescriptions.services.ocr_file_to_text")
    def test_empty_ocr_result_is_graceful_failure(self, mock_ocr):
        self.login()
        mock_ocr.return_value = OCRResult(text="   ")

        resp = self.client.post(reverse("prescriptions:upload"), {"file": self.make_png_upload()})
        self.assertEqual(resp.status_code, 302)

        prescription = Prescription.objects.first()
        prescription.refresh_from_db()
        self.assertEqual(prescription.processing_status, Prescription.ProcessingStatus.FAILED)
        self.assertIn("No text could be extracted", prescription.processing_error)


class PrescriptionAPITests(APITestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

        storage = PrivatePrescriptionStorage(location=Path(self.tmpdir.name) / "private_uploads")
        Prescription._meta.get_field("uploaded_file").storage = storage

        self.patient = User.objects.create_user(
            email="api-patient@example.com",
            password="StrongPass123",
            name="Patient",
            role=User.Role.PATIENT,
        )
        self.other_patient = User.objects.create_user(
            email="api-patient2@example.com",
            password="StrongPass123",
            name="Other",
            role=User.Role.PATIENT,
        )
        self.admin = User.objects.create_user(
            email="api-admin@example.com",
            password="StrongPass123",
            name="Admin",
            role=User.Role.ADMIN,
            is_staff=True,
        )

        self.m1 = Medicine.objects.create(
            brand_name="Paracetamol",
            generic_name="Paracetamol",
            composition="Paracetamol",
            strength="650mg",
            dosage_form=Medicine.DosageForm.TABLET,
            manufacturer="Test",
        )
        self.m2 = Medicine.objects.create(
            brand_name="Paracetamol Extra",
            generic_name="Paracetamol",
            composition="Paracetamol",
            strength="650mg",
            dosage_form=Medicine.DosageForm.TABLET,
            manufacturer="Test2",
        )

    def make_png_upload(self, name="rx.png"):
        try:
            from PIL import Image
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("PIL is required for prescription tests") from exc

        buf = BytesIO()
        Image.new("RGB", (10, 10), color=(255, 255, 255)).save(buf, format="PNG")
        return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")

    @patch("prescriptions.services.ocr_file_to_text")
    def test_api_upload_confirm_and_ownership(self, mock_ocr):
        mock_ocr.return_value = OCRResult(text="Paracetmol 650")

        self.client.force_authenticate(user=self.patient)
        resp = self.client.post(
            reverse("prescriptions_api:list-create"),
            {"file": self.make_png_upload()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        prescription_id = resp.data["id"]
        self.assertEqual(resp.data["processing_status"], "processed")
        self.assertTrue(resp.data["detected_medicines"])

        detected_id = resp.data["detected_medicines"][0]["id"]
        confirm_resp = self.client.post(
            reverse("prescriptions_api:confirm", args=[prescription_id]),
            {"items": [{"id": detected_id, "confirmed": True, "medicine_id": self.m1.id}]},
            format="json",
        )
        self.assertEqual(confirm_resp.status_code, status.HTTP_200_OK)
        pm = PrescriptionMedicine.objects.get(pk=detected_id)
        self.assertTrue(pm.user_confirmed)
        self.assertEqual(pm.confirmation_status, PrescriptionMedicine.ConfirmationStatus.CONFIRMED)
        self.assertEqual(pm.medicine_id, self.m1.id)

        # Other patient cannot access.
        self.client.force_authenticate(user=self.other_patient)
        resp_other = self.client.get(reverse("prescriptions_api:detail", args=[prescription_id]))
        self.assertEqual(resp_other.status_code, status.HTTP_404_NOT_FOUND)

        # Admin can access.
        self.client.force_authenticate(user=self.admin)
        resp_admin = self.client.get(reverse("prescriptions_api:detail", args=[prescription_id]))
        self.assertEqual(resp_admin.status_code, status.HTTP_200_OK)

    @patch("prescriptions.services.ocr_file_to_text")
    def test_api_ocr_endpoint_graceful_failure(self, mock_ocr):
        mock_ocr.side_effect = OCRUnavailableError("missing")

        self.client.force_authenticate(user=self.patient)
        resp = self.client.post(
            reverse("prescriptions_api:list-create"),
            {"file": self.make_png_upload()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        prescription_id = resp.data["id"]

        resp_ocr = self.client.get(reverse("prescriptions_api:ocr", args=[prescription_id]))
        self.assertEqual(resp_ocr.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_ocr.data["processing_status"], "failed")
