from django.contrib import admin
from django.utils.html import format_html

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "industry", "size", "created_at", "deleted_status"]
    list_filter = ["size", "industry"]
    search_fields = ["name", "owner__username"]
    readonly_fields = ["id", "name_lower", "created_at", "updated_at", "deleted_at", "deleted_by"]
    # Show ALL accounts including soft-deleted
    def get_queryset(self, request):
        return Account.all_objects.all()

    @admin.display(description="Deleted")
    def deleted_status(self, obj):
        if obj.is_deleted:
            return format_html('<span style="color:red;">✗ {}</span>', str(obj.deleted_at.date()))
        return format_html('<span style="color:green;">✓ Active</span>')

    actions = ["restore_accounts"]

    @admin.action(description="Restore selected accounts")
    def restore_accounts(self, request, queryset):
        count = queryset.update(deleted_at=None, deleted_by=None)
        self.message_user(request, f"{count} account(s) restored.")
