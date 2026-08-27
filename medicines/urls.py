from django.urls import path

from . import views

app_name = "medicines"

urlpatterns = [
    path("search/", views.search_page, name="search"),
    path("<int:id>/", views.detail, name="detail"),
]
