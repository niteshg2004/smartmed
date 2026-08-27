from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User


class UserModelTests(TestCase):
    def test_create_user_defaults_to_patient_role(self):
        user = User.objects.create_user(email="patient@example.com", password="StrongPass123", name="Pat")
        self.assertEqual(user.role, User.Role.PATIENT)
        self.assertTrue(user.check_password("StrongPass123"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_create_superuser_is_admin_role_and_staff(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="StrongPass123", name="Admin")
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_email_is_unique(self):
        User.objects.create_user(email="dup@example.com", password="StrongPass123", name="A")
        with self.assertRaises(Exception):
            User.objects.create_user(email="dup@example.com", password="StrongPass123", name="B")


class RegisterAPITests(APITestCase):
    def setUp(self):
        self.url = reverse("accounts_api:register")

    def test_register_patient_succeeds(self):
        payload = {
            "name": "Alice",
            "email": "alice@example.com",
            "phone": "9999999999",
            "password": "StrongPass123",
            "role": "patient",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertTrue(User.objects.filter(email="alice@example.com").exists())

    def test_register_pharmacy_role_succeeds(self):
        payload = {
            "name": "City Pharmacy Owner",
            "email": "owner@example.com",
            "password": "StrongPass123",
            "role": "pharmacy",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_admin_role_is_rejected(self):
        payload = {
            "name": "Sneaky",
            "email": "sneaky@example.com",
            "password": "StrongPass123",
            "role": "admin",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="sneaky@example.com").exists())

    def test_register_weak_password_is_rejected(self):
        payload = {
            "name": "Weak",
            "email": "weak@example.com",
            "password": "123",
            "role": "patient",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email_is_rejected(self):
        User.objects.create_user(email="taken@example.com", password="StrongPass123", name="First")
        payload = {
            "name": "Second",
            "email": "taken@example.com",
            "password": "StrongPass123",
            "role": "patient",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="bob@example.com", password="StrongPass123", name="Bob")
        self.url = reverse("accounts_api:login")

    def test_login_with_correct_credentials_succeeds(self):
        response = self.client.post(
            self.url, {"email": "bob@example.com", "password": "StrongPass123"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            self.url, {"email": "bob@example.com", "password": "WrongPassword"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_unknown_email_fails(self):
        response = self.client.post(
            self.url, {"email": "nobody@example.com", "password": "StrongPass123"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MeAndLogoutAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="carol@example.com", password="StrongPass123", name="Carol")

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("accounts_api:me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user_when_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("accounts_api:me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "carol@example.com")

    def test_logout_requires_authentication(self):
        response = self.client.post(reverse("accounts_api:logout"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
