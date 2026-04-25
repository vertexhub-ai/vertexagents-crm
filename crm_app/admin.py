from django.contrib import admin

from .models import Account, Contact, Lead, Opportunity


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'company_name', 'status', 'owner', 'created_at']
    list_filter = ['status']
    search_fields = ['first_name', 'last_name', 'email', 'company_name']
    readonly_fields = ['converted_contact', 'converted_account', 'converted_opportunity', 'converted_at']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'account', 'owner', 'created_at']
    search_fields = ['first_name', 'last_name', 'email']


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ['name', 'stage', 'account', 'owner', 'amount', 'expected_close_date']
    list_filter = ['stage']
    search_fields = ['name']
