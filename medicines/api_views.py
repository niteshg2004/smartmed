from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Medicine, SearchHistory
from .search import search_medicines
from .serializers import (
    MedicineSearchResultSerializer,
    MedicineSerializer,
    SearchHistorySerializer,
)


class MedicineSearchAPIView(APIView):
    """
    GET /api/v1/medicines/search/?q=paracetmol%20650&limit=10

    Fuzzy-matches the query against brand/generic/composition names.
    Logs a SearchHistory row for authenticated users (used later as an ML
    demand-signal feature — see Section 8/InventoryHistory features).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            raise ValidationError({"q": "Query parameter 'q' is required."})
        if len(query) > 200:
            raise ValidationError({"q": "Query is too long (max 200 characters)."})

        try:
            limit = int(request.query_params.get("limit", 10))
        except ValueError:
            raise ValidationError({"limit": "Must be an integer."})
        limit = max(1, min(limit, 50))

        matches = search_medicines(query, limit=limit)

        SearchHistory.objects.create(
            user=request.user,
            medicine=matches[0].medicine if matches else None,
            query_text=query,
            latitude=self._parse_float(request.query_params.get("lat")),
            longitude=self._parse_float(request.query_params.get("lng")),
            location_text=request.query_params.get("location", ""),
        )

        data = [
            {"medicine": m.medicine, "confidence": m.confidence, "matched_on": m.matched_on}
            for m in matches
        ]
        serializer = MedicineSearchResultSerializer(data, many=True)
        return Response({"query": query, "count": len(data), "results": serializer.data})

    @staticmethod
    def _parse_float(value):
        if value in (None, ""):
            return None
        try:
            return float(value)
        except ValueError:
            return None


class MedicineDetailAPIView(generics.RetrieveAPIView):
    """GET /api/v1/medicines/{id}/"""

    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    permission_classes = [permissions.IsAuthenticated]


class MySearchHistoryAPIView(generics.ListAPIView):
    """GET /api/v1/medicines/search-history/ — the current user's own searches."""

    serializer_class = SearchHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SearchHistory.objects.filter(user=self.request.user).select_related("medicine")
