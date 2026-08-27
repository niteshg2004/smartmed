from django.contrib import admin

from .models import AlternativeCandidate


@admin.register(AlternativeCandidate)
class AlternativeCandidateAdmin(admin.ModelAdmin):
    list_display = [
        "medicine", "candidate_medicine", "matching_basis",
        "confidence_score", "verification_status", "verified_by", "created_at",
    ]
    list_filter = ["verification_status", "matching_basis"]
    search_fields = ["medicine__brand_name", "candidate_medicine__brand_name"]
    readonly_fields = ["created_at", "verified_at"]
    autocomplete_fields = ["medicine", "candidate_medicine", "verified_by"]
