from django.urls import path

from . import views

app_name = "predictions"

urlpatterns = [
    path("analytics/", views.analytics_view, name="analytics"),
]
