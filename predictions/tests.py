import tempfile
from datetime import timedelta
from pathlib import Path

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from inventory.models import Inventory, InventoryHistory
from medicines.models import Medicine
from ml.predict import predict_stock
from ml.train import train_and_save
from pharmacies.models import Pharmacy


class StockPredictionTestDataMixin:
    def create_prediction_dataset(self):
        owner = User.objects.create_user(
            email="pharmacy-owner@example.com",
            password="StrongPass123",
            name="Pharmacy Owner",
            role=User.Role.PHARMACY,
        )
        patient = User.objects.create_user(
            email="patient@example.com",
            password="StrongPass123",
            name="Patient",
            role=User.Role.PATIENT,
        )
        pharmacies = [
            Pharmacy.objects.create(
                owner=owner,
                name="City Pharmacy",
                address="Main Street",
                latitude=18.52,
                longitude=73.86,
                verification_status=Pharmacy.VerificationStatus.VERIFIED,
                is_demo_data=True,
            ),
            Pharmacy.objects.create(
                owner=owner,
                name="Care Pharmacy",
                address="Second Street",
                latitude=18.53,
                longitude=73.87,
                verification_status=Pharmacy.VerificationStatus.VERIFIED,
                is_demo_data=True,
            ),
        ]
        medicines = [
            Medicine.objects.create(
                brand_name="Dolo 650",
                generic_name="Paracetamol",
                composition="Paracetamol",
                strength="650mg",
                dosage_form=Medicine.DosageForm.TABLET,
                manufacturer="Micro Labs",
                therapeutic_category="Analgesic / Antipyretic",
                is_demo_data=True,
            ),
            Medicine.objects.create(
                brand_name="Pantocid 40",
                generic_name="Pantoprazole",
                composition="Pantoprazole",
                strength="40mg",
                dosage_form=Medicine.DosageForm.TABLET,
                manufacturer="Sun Pharma",
                therapeutic_category="Antacid / PPI",
                prescription_required=True,
                is_demo_data=True,
            ),
        ]

        base_date = timezone.now() - timedelta(days=90)
        latest_inventory = None
        for pharmacy_index, pharmacy in enumerate(pharmacies):
            for medicine_index, medicine in enumerate(medicines):
                quantity = 160 + (pharmacy_index * 20) + (medicine_index * 15)
                for day in range(75):
                    ts = base_date + timedelta(days=day, hours=10 + pharmacy_index)
                    baseline = 4 + medicine_index + (2 if ts.weekday() in [0, 1] else 0)
                    daily_demand = baseline + ((day + pharmacy_index) % 3)
                    quantity = max(0, quantity - daily_demand)
                    if quantity < 18 or day % (10 + medicine_index) == 0:
                        quantity += 45 + ((day + medicine_index) % 18)

                    InventoryHistory.objects.create(
                        pharmacy=pharmacy,
                        medicine=medicine,
                        quantity=quantity,
                        timestamp=ts,
                        is_demo_data=True,
                    )

                latest_inventory = Inventory.objects.create(
                    pharmacy=pharmacy,
                    medicine=medicine,
                    quantity=quantity,
                    is_demo_data=True,
                )
        return {
            "owner": owner,
            "patient": patient,
            "inventory": latest_inventory,
        }


class StockModelTrainingTests(StockPredictionTestDataMixin, TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        override = override_settings(BASE_DIR=Path(self.tmpdir.name))
        override.enable()
        self.addCleanup(override.disable)
        self.data = self.create_prediction_dataset()

    def test_train_and_save_creates_model_and_metadata(self):
        output_dir = Path(self.tmpdir.name) / "ml" / "models"
        result = train_and_save(output_dir=output_dir)

        self.assertIn(result.best_model_name, {"linear_regression", "random_forest"})
        self.assertTrue(result.model_path.exists())
        self.assertTrue(result.metadata_path.exists())
        self.assertIn("mae", result.metrics[result.best_model_name])
        self.assertIn("rmse", result.metrics[result.best_model_name])
        self.assertIn("r2", result.metrics[result.best_model_name])

    def test_predict_stock_uses_trained_model(self):
        train_and_save(output_dir=Path(self.tmpdir.name) / "ml" / "models")
        inventory = self.data["inventory"]

        result = predict_stock(
            pharmacy_id=inventory.pharmacy_id,
            medicine_id=inventory.medicine_id,
            horizon_days=7,
        )

        self.assertGreaterEqual(result.predicted_demand, 0)
        self.assertGreaterEqual(result.predicted_remaining_stock, 0)
        self.assertGreaterEqual(result.stockout_probability, 0)
        self.assertLessEqual(result.stockout_probability, 1)
        self.assertIn(result.risk, {"LOW", "MEDIUM", "HIGH"})
        self.assertEqual(result.model_info["best_model"] in {"linear_regression", "random_forest"}, True)


class PredictionAPITests(StockPredictionTestDataMixin, APITestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        override = override_settings(BASE_DIR=Path(self.tmpdir.name))
        override.enable()
        self.addCleanup(override.disable)
        self.data = self.create_prediction_dataset()
        train_and_save(output_dir=Path(self.tmpdir.name) / "ml" / "models")

    def test_prediction_api_requires_authentication(self):
        self.client.force_authenticate(user=None)
        inventory = self.data["inventory"]
        response = self.client.get(
            reverse("predictions_api:predict"),
            {"pharmacy_id": inventory.pharmacy_id, "medicine_id": inventory.medicine_id},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_prediction_api_returns_prediction_payload(self):
        self.client.force_authenticate(user=self.data["patient"])
        inventory = self.data["inventory"]
        response = self.client.get(
            reverse("predictions_api:predict"),
            {"pharmacy_id": inventory.pharmacy_id, "medicine_id": inventory.medicine_id, "horizon_days": 5},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("predicted_next_day_demand", response.data)
        self.assertIn("stockout_probability", response.data)
        self.assertIn("model_info", response.data)
