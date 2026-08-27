from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.inventory_list, name='list'),
    path('update/<int:medicine_id>/', views.inventory_update, name='update'),
    path('add/', views.inventory_add, name='add'),
    path("requests/", views.availability_requests_my, name="requests-my"),
    path("requests/new/", views.availability_request_new, name="request-new"),
    path("requests/inbox/", views.availability_requests_inbox, name="requests-inbox"),
    path("requests/<int:pk>/respond/", views.availability_request_respond, name="request-respond"),
]
