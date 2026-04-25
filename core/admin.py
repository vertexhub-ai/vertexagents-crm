from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Account, Activity, Contact, Lead, Opportunity, User


class SoftDeleteAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.all_objects.all()

    actions = ["restore_selected"]

    @admin.action(description="Restore selected records")
    def restore_selected(self, request, queryset):
        queryset.update(deleted_at=None, deleted_by=None)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (("Role", {"fields": ("role",)}),)
    list_display = ["username", "email", "first_name", "last_name", "role", "is_staff"]
    list_filter = ["role", "is_staff", "is_superuser"]


@admin.register(Account)
class AccountAdmin(SoftDeleteAdmin):
    list_display = ["name", "industry", "size", "owner", "created_at", "deleted_at"]
    search_fields = ["name", "website"]
    list_filter = ["size", "deleted_at"]
    readonly_fields = ["created_at", "updated_at", "deleted_at", "deleted_by"]


@admin.register(Contact)
class ContactAdmin(SoftDeleteAdmin):
    list_display = ["full_name", "email", "account", "owner", "created_at", "deleted_at"]
    search_fields = ["first_name", "last_name", "email"]
    list_filter = ["deleted_at"]
    readonly_fields = ["created_at", "updated_at", "deleted_at", "deleted_by", "source_lead"]

    @admin.display(description="Name")
    def full_name(self, obj):
        return obj.full_name


@admin.register(Lead)
class LeadAdmin(SoftDeleteAdmin):
    list_display = [
        "full_name", "email", "company_name", "status", "source", "owner",
        "created_at", "deleted_at",
    ]
    search_fields = ["first_name", "last_name", "email", "company_name"]
    list_filter = ["status", "source", "deleted_at"]
    readonly_fields = [
        "created_at", "updated_at", "deleted_at", "deleted_by",
        "converted_contact", "converted_account", "converted_opportunity", "converted_at",
    ]

    @admin.display(description="Name")
    def full_name(self, obj):
        return obj.full_name


@admin.register(Opportunity)
class OpportunityAdmin(SoftDeleteAdmin):
    list_display = [
        "name", "stage", "amount_display", "account", "owner",
        "expected_close_date", "deleted_at",
    ]
    search_fields = ["name"]
    list_filter = ["stage", "currency", "deleted_at"]
    readonly_fields = [
        "created_at", "updated_at", "deleted_at", "deleted_by",
        "closed_at", "amount_display",
    ]

    @admin.display(description="Amount")
    def amount_display(self, obj):
        return obj.amount_display


@admin.register(Activity)
class ActivityAdmin(SoftDeleteAdmin):
    list_display = ["subject", "kind", "owner", "due_at", "completed_at", "deleted_at"]
    search_fields = ["subject", "body"]
    list_filter = ["kind", "deleted_at"]
    readonly_fields = ["created_at", "updated_at", "deleted_at", "deleted_by"]
