from django.urls import path

from . import api_views

app_name = "accounts_api"

urlpatterns = [
    path("register/", api_views.RegisterAPIView.as_view(), name="register"),
    path("login/", api_views.LoginAPIView.as_view(), name="login"),
    path("logout/", api_views.LogoutAPIView.as_view(), name="logout"),
    path("me/", api_views.MeAPIView.as_view(), name="me"),
]
