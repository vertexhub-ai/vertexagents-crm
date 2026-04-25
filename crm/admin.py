from django.contrib import admin
from .models import Lead, Contact, Account, Opportunity, Activity


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "status", "deleted_at")
    list_filter = ("status",)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "account", "deleted_at")


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "deleted_at")


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("name", "stage", "amount", "close_date", "deleted_at")


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("kind", "subject", "author", "created_at", "deleted_at")
    list_filter = ("kind",)
