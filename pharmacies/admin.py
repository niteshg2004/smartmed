from django.contrib import admin

from .models import Pharmacy


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "verification_status", "latitude", "longitude", "is_demo_data"]
    list_filter = ["verification_status", "is_demo_data"]
    search_fields = ["name", "address", "owner__email"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["owner"]
