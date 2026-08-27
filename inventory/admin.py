from django.contrib import admin

from .models import AvailabilityRequest, Inventory, InventoryHistory


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ["medicine", "pharmacy", "quantity", "availability_status", "last_updated", "is_demo_data"]
    list_filter = ["availability_status", "is_demo_data"]
    search_fields = ["medicine__brand_name", "pharmacy__name"]
    readonly_fields = ["last_updated", "availability_status"]
    autocomplete_fields = ["pharmacy", "medicine"]


@admin.register(InventoryHistory)
class InventoryHistoryAdmin(admin.ModelAdmin):
    list_display = ["medicine", "pharmacy", "quantity", "timestamp", "is_demo_data"]
    list_filter = ["is_demo_data"]
    search_fields = ["medicine__brand_name", "pharmacy__name"]
    readonly_fields = ["timestamp"]


@admin.register(AvailabilityRequest)
class AvailabilityRequestAdmin(admin.ModelAdmin):
    list_display = ["medicine", "pharmacy", "user", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["medicine__brand_name", "pharmacy__name", "user__email"]
    readonly_fields = ["created_at", "updated_at"]
