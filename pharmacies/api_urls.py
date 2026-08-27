from django.urls import path
from . import api_views

app_name = 'pharmacies_api'

urlpatterns = [
    path('', api_views.PharmacyListCreateAPIView.as_view(), name='pharmacy-list-create'),
    path('<int:pk>/', api_views.PharmacyDetailAPIView.as_view(), name='pharmacy-detail'),
    path('nearby/', api_views.NearbyPharmaciesAPIView.as_view(), name='pharmacy-nearby'),
]
