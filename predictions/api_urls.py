"""Stock-out prediction endpoints implemented in Phase 5."""
from django.urls import path

from . import api_views

app_name = "predictions_api"

urlpatterns = [
    path("", api_views.PredictionAPIView.as_view(), name="predict"),
]
