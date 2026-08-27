from django.urls import path

from . import api_views

app_name = "medicines_api"

urlpatterns = [
    path("search/", api_views.MedicineSearchAPIView.as_view(), name="search"),
    path("search-history/", api_views.MySearchHistoryAPIView.as_view(), name="search-history"),
    path("<int:pk>/", api_views.MedicineDetailAPIView.as_view(), name="detail"),
]
