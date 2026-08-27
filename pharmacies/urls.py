from django.urls import path
from . import views

app_name = 'pharmacies'

urlpatterns = [
    path('dashboard/', views.pharmacy_dashboard, name='dashboard'),
    path('create/', views.pharmacy_create, name='create'),
    path('<int:pk>/edit/', views.pharmacy_edit, name='edit'),
    path('view/<int:pk>/', views.pharmacy_public_detail, name='public-detail'),
    path('nearby/<int:medicine_id>/', views.nearby_pharmacies, name='nearby-medicine'),
    path('', views.pharmacy_list, name='list'),
]
