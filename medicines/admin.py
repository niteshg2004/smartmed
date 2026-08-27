from django.contrib import admin

from .models import Medicine, SearchHistory


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = [
        "brand_name", "generic_name", "strength", "dosage_form",
        "therapeutic_category", "prescription_required", "is_demo_data",
    ]
    list_filter = ["dosage_form", "prescription_required", "therapeutic_category", "is_demo_data"]
    search_fields = ["brand_name", "generic_name", "composition", "manufacturer"]
    readonly_fields = ["normalized_search_key", "created_at", "updated_at"]


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ["user", "query_text", "medicine", "timestamp"]
    list_filter = ["timestamp"]
    search_fields = ["query_text", "user__email"]
    readonly_fields = ["timestamp"]
