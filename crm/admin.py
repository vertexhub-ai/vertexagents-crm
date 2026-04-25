from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CRMUser, Account, Contact


@admin.register(CRMUser)
class CRMUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("CRM", {"fields": ("role",)}),)
    list_display = ["username", "email", "role", "is_staff"]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "created_at", "deleted_at"]
    list_filter = ["deleted_at"]
    search_fields = ["name"]

    def get_queryset(self, request):
        return Account.all_objects.all()


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "account", "owner", "created_at", "deleted_at"]
    list_filter = ["deleted_at"]
    search_fields = ["first_name", "last_name", "email"]

    def get_queryset(self, request):
        return Contact.all_objects.all()
