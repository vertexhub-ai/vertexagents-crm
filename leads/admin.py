from django.contrib import admin
from django.utils.html import format_html

from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = [
        "last_name",
        "first_name",
        "company_name",
        "email",
        "status",
        "source",
        "owner",
        "converted_at",
        "deleted_at",
        "created_at",
        "deleted_status",
    ]
    list_filter = ["status", "source", "owner", "deleted_at"]
    search_fields = ["first_name", "last_name", "email", "phone", "company_name", "title"]
    # Conversion audit fields are write-once via the V-176 conversion flow; admin
    # only observes them. The "Undo a wrong lead conversion" runbook in README
    # explains how to reverse a conversion safely.
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "deleted_by",
        "converted_contact",
        "converted_account",
        "converted_opportunity",
        "converted_at",
    ]
    raw_id_fields = ["owner"]
    ordering = ["-created_at"]

    def get_queryset(self, request):
        return Lead.all_objects.all()

    @admin.display(description="Deleted")
    def deleted_status(self, obj):
        if obj.deleted_at is not None:
            return format_html('<span style="color:red;">✗ {}</span>', str(obj.deleted_at.date()))
        return format_html('<span style="color:green;">✓ Active</span>')

    actions = ["restore_leads"]

    @admin.action(description="Restore selected leads")
    def restore_leads(self, request, queryset):
        count = queryset.update(deleted_at=None, deleted_by=None)
        self.message_user(request, f"{count} lead(s) restored.")
