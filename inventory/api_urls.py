from django.urls import path
from . import api_views

app_name = 'inventory_api'

urlpatterns = [
    path('', api_views.InventoryListAPIView.as_view(), name='inventory-list'),
    path('update/<int:pharmacy_id>/<int:medicine_id>/', api_views.InventoryUpdateAPIView.as_view(), name='inventory-update'),
    path('history/<int:pharmacy_id>/<int:medicine_id>/', api_views.InventoryHistoryAPIView.as_view(), name='inventory-history'),
    path('availability/', api_views.AvailabilityAPIView.as_view(), name='availability'),
    path('request/', api_views.AvailabilityRequestCreateAPIView.as_view(), name='request-create'),
    path('request/<int:pk>/respond/', api_views.AvailabilityRequestRespondAPIView.as_view(), name='request-respond'),
    path('requests/my/', api_views.MyAvailabilityRequestsAPIView.as_view(), name='requests-my'),
    path('requests/inbox/', api_views.PharmacyAvailabilityInboxAPIView.as_view(), name='requests-inbox'),
]
