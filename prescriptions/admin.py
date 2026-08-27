from django.contrib import admin

from .models import Prescription, PrescriptionMedicine


class PrescriptionMedicineInline(admin.TabularInline):
    model = PrescriptionMedicine
    extra = 0
    readonly_fields = ["extracted_name", "extracted_strength", "match_confidence", "confirmation_status"]


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    """
    Deliberately does NOT display extracted_text in list_display or make it
    searchable admin-wide — prescription content is sensitive (Section 16)
    and should only be opened deliberately on a single record's detail page.
    """
    list_display = ["id", "user", "processing_status", "created_at"]
    list_filter = ["processing_status"]
    readonly_fields = ["created_at"]
    inlines = [PrescriptionMedicineInline]

    def get_queryset(self, request):
        # Admins can review for moderation/debugging; still owner-scoped
        # everywhere else in the app (web/API views use IsOwnerOrAdmin).
        return super().get_queryset(request)
