"""
Project-wide smoke tests: confirms the URLConf resolves and the app registry
is wired correctly. Per-app business-logic tests live in each app's tests.py
(e.g. accounts/tests.py). This file is what CI / `manage.py test tests`
should run first, since a failure here means something structural broke.
"""
from django.apps import apps
from django.test import TestCase
from django.urls import reverse


class URLResolutionSmokeTests(TestCase):
    def test_admin_url_resolves(self):
        self.assertEqual(reverse("admin:index"), "/admin/")

    def test_dashboard_home_resolves(self):
        self.assertEqual(reverse("dashboard:home"), "/")

    def test_accounts_urls_resolve(self):
        self.assertEqual(reverse("accounts:login"), "/accounts/login/")
        self.assertEqual(reverse("accounts:register"), "/accounts/register/")
        self.assertEqual(reverse("accounts:logout"), "/accounts/logout/")

    def test_accounts_api_urls_resolve(self):
        self.assertEqual(reverse("accounts_api:register"), "/api/v1/auth/register/")
        self.assertEqual(reverse("accounts_api:login"), "/api/v1/auth/login/")
        self.assertEqual(reverse("accounts_api:logout"), "/api/v1/auth/logout/")
        self.assertEqual(reverse("accounts_api:me"), "/api/v1/auth/me/")


class AppRegistrySmokeTests(TestCase):
    def test_all_expected_local_apps_are_installed(self):
        expected = {
            "accounts", "medicines", "pharmacies", "inventory",
            "prescriptions", "alternatives", "predictions", "dashboard",
        }
        installed = {cfg.name for cfg in apps.get_app_configs()}
        self.assertTrue(expected.issubset(installed))

    def test_core_models_are_registered(self):
        expected_models = {
            ("accounts", "user"),
            ("medicines", "medicine"),
            ("medicines", "searchhistory"),
            ("pharmacies", "pharmacy"),
            ("inventory", "inventory"),
            ("inventory", "inventoryhistory"),
            ("inventory", "availabilityrequest"),
            ("prescriptions", "prescription"),
            ("prescriptions", "prescriptionmedicine"),
            ("alternatives", "alternativecandidate"),
        }
        for app_label, model_name in expected_models:
            with self.subTest(app_label=app_label, model_name=model_name):
                self.assertTrue(apps.is_installed(app_label))
                apps.get_model(app_label, model_name)  # raises LookupError if missing
