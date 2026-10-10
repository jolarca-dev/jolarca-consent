"""Admin configuration for consent_registry."""

from django.contrib import admin

from .models import ConsentRecord


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    """Admin interface for ConsentRecord (read-only)."""

    list_display = [
        "subject_id",
        "purpose",
        "consent_version",
        "granted",
        "timestamp",
        "anonymized_at",
    ]
    list_filter = ["purpose", "granted", "consent_version", "anonymized_at"]
    search_fields = ["subject_id"]
    readonly_fields = [
        "id",
        "subject_id",
        "purpose",
        "consent_version",
        "granted",
        "ip_address",
        "user_agent",
        "timestamp",
        "revoked_at",
        "prev_hash",
        "entry_hash",
        "created_at",
        "anonymized_at",
    ]

    def has_add_permission(self, request):
        """Prevent adding records via admin (append-only via API)."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent changing records via admin (immutable)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting records via admin (ADR-0003)."""
        return False
