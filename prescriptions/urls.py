from django.urls import path

from . import views

app_name = "prescriptions"

urlpatterns = [
    path("", views.prescription_list_view, name="list"),
    path("upload/", views.prescription_upload_view, name="upload"),
    path("<int:pk>/", views.prescription_detail_view, name="detail"),
    path("<int:pk>/file/", views.prescription_file_view, name="file"),
]

