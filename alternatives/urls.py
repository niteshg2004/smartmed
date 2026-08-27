from django.urls import path

from . import views

app_name = "alternatives"

urlpatterns = [
    path("verify/", views.verification_queue_view, name="verification-queue"),
]
