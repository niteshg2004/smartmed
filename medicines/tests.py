from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import Medicine, SearchHistory, normalize_text
from .search import search_medicines


def make_medicine(**kwargs):
    defaults = dict(
        brand_name="Dolo",
        generic_name="Paracetamol",
        composition="Paracetamol",
        strength="650mg",
        dosage_form=Medicine.DosageForm.TABLET,
        manufacturer="Micro Labs",
        therapeutic_category="Analgesic",
        prescription_required=False,
    )
    defaults.update(kwargs)
    return Medicine.objects.create(**defaults)


class NormalizeTextTests(TestCase):
    def test_lowercases_and_strips_punctuation(self):
        self.assertEqual(normalize_text("Dolo-650 (Tablet)"), "dolo 650 tablet")

    def test_collapses_whitespace(self):
        self.assertEqual(normalize_text("Para   cetamol   650"), "para cetamol 650")

    def test_empty_string_is_safe(self):
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text(None), "")


class MedicineSearchEngineTests(TestCase):
    def setUp(self):
        self.dolo_650 = make_medicine(brand_name="Dolo", strength="650mg")
        self.dolo_500 = make_medicine(brand_name="Dolo", strength="500mg", generic_name="Paracetamol")
        self.crocin_650 = make_medicine(
            brand_name="Crocin", strength="650mg", generic_name="Paracetamol", composition="Paracetamol",
            manufacturer="GSK",
        )
        self.amox = make_medicine(
            brand_name="Amoxyclav", generic_name="Amoxicillin", composition="Amoxicillin + Clavulanic Acid",
            strength="500mg", manufacturer="Cipla",
        )

    def test_exact_brand_and_strength_is_top_match(self):
        results = search_medicines("Dolo 650")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].medicine, self.dolo_650)

    def test_typo_tolerant_generic_name_match(self):
        results = search_medicines("paracetmol")
        matched_ids = {r.medicine.id for r in results}
        self.assertIn(self.dolo_650.id, matched_ids)
        self.assertIn(self.crocin_650.id, matched_ids)

    def test_strength_token_disambiguates_same_brand(self):
        results = search_medicines("Dolo 500")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].medicine, self.dolo_500)

    def test_unrelated_query_returns_no_or_low_confidence_results(self):
        results = search_medicines("xyzunrelatedmedicinequery12345")
        self.assertEqual(results, [])

    def test_empty_query_returns_empty_list(self):
        self.assertEqual(search_medicines(""), [])
        self.assertEqual(search_medicines("   "), [])

    def test_results_are_ranked_by_confidence_descending(self):
        results = search_medicines("paracetamol")
        scores = [r.confidence for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_composition_match_for_combination_drug(self):
        results = search_medicines("amoxicillin clavulanic acid")
        matched_ids = {r.medicine.id for r in results}
        self.assertIn(self.amox.id, matched_ids)


class MedicineSearchAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="searcher@example.com", password="StrongPass123", name="S")
        self.client.force_authenticate(user=self.user)
        self.medicine = make_medicine()
        self.url = reverse("medicines_api:search")

    def test_search_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url, {"q": "dolo"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_requires_query_param(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_returns_ranked_results(self):
        response = self.client.get(self.url, {"q": "dolo 650"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["medicine"]["brand_name"], "Dolo")

    def test_search_logs_search_history(self):
        self.assertEqual(SearchHistory.objects.count(), 0)
        self.client.get(self.url, {"q": "dolo 650"})
        self.assertEqual(SearchHistory.objects.count(), 1)
        entry = SearchHistory.objects.first()
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.query_text, "dolo 650")

    def test_search_rejects_overly_long_query(self):
        response = self.client.get(self.url, {"q": "a" * 300})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MedicineDetailAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="viewer@example.com", password="StrongPass123", name="V")
        self.client.force_authenticate(user=self.user)
        self.medicine = make_medicine()

    def test_detail_returns_medicine(self):
        response = self.client.get(reverse("medicines_api:detail", args=[self.medicine.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["brand_name"], "Dolo")

    def test_detail_404_for_unknown_id(self):
        response = self.client.get(reverse("medicines_api:detail", args=[999999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SearchHistoryAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="hist@example.com", password="StrongPass123", name="H")
        self.other_user = User.objects.create_user(email="other@example.com", password="StrongPass123", name="O")
        self.client.force_authenticate(user=self.user)
        self.medicine = make_medicine()

    def test_history_is_scoped_to_current_user(self):
        SearchHistory.objects.create(user=self.user, medicine=self.medicine, query_text="dolo")
        SearchHistory.objects.create(user=self.other_user, medicine=self.medicine, query_text="crocin")

        response = self.client.get(reverse("medicines_api:search-history"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["query_text"], "dolo")
