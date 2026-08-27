"""
Root URL configuration.

Web (server-rendered) routes live at the root; JSON API routes live under
/api/v1/. Each app owns its own urls.py (web + api split per app where
relevant) so this file stays a thin router.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Server-rendered UI
    path("", include("dashboard.urls", namespace="dashboard")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("medicines/", include("medicines.urls", namespace="medicines")),
    path("pharmacies/", include("pharmacies.urls", namespace="pharmacies")),
    path("inventory/", include("inventory.urls", namespace="inventory")),
    path("prescriptions/", include("prescriptions.urls", namespace="prescriptions")),
    path("alternatives/", include("alternatives.urls", namespace="alternatives")),
    path("predictions/", include("predictions.urls", namespace="predictions")),

    # JSON API
    path("api/v1/auth/", include("accounts.api_urls", namespace="accounts_api")),
    path("api/v1/medicines/", include("medicines.api_urls", namespace="medicines_api")),
    path("api/v1/pharmacies/", include("pharmacies.api_urls", namespace="pharmacies_api")),
    path("api/v1/inventory/", include("inventory.api_urls", namespace="inventory_api")),
    path("api/v1/prescriptions/", include("prescriptions.api_urls", namespace="prescriptions_api")),
    path("api/v1/alternatives/", include("alternatives.api_urls", namespace="alternatives_api")),
    path("api/v1/predictions/", include("predictions.api_urls", namespace="predictions_api")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
