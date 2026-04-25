from django.urls import path
from crm import views

urlpatterns = [
    # Leads
    path("leads/", views.lead_list, name="lead_list"),
    path("leads/<uuid:pk>/", views.lead_detail, name="lead_detail"),
    path("leads/<uuid:pk>/activity/", views.lead_activity_create, name="lead_activity_create"),

    # Contacts
    path("contacts/", views.contact_list, name="contact_list"),
    path("contacts/<uuid:pk>/", views.contact_detail, name="contact_detail"),
    path("contacts/<uuid:pk>/activity/", views.contact_activity_create, name="contact_activity_create"),

    # Accounts
    path("accounts/", views.account_list, name="account_list"),
    path("accounts/<uuid:pk>/", views.account_detail, name="account_detail"),
    path("accounts/<uuid:pk>/activity/", views.account_activity_create, name="account_activity_create"),

    # Opportunities
    path("opportunities/", views.opportunity_list, name="opportunity_list"),
    path("opportunities/<uuid:pk>/", views.opportunity_detail, name="opportunity_detail"),
    path("opportunities/<uuid:pk>/activity/", views.opportunity_activity_create, name="opportunity_activity_create"),

    # Activity actions
    path("activity/<uuid:pk>/complete/", views.activity_complete, name="activity_complete"),
    path("activity/<uuid:pk>/edit/", views.activity_edit, name="activity_edit"),
    path("activity/<uuid:pk>/delete/", views.activity_delete, name="activity_delete"),
]
