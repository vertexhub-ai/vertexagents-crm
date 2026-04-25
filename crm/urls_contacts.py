from django.urls import path
from crm.views.contacts import contact_list, contact_detail, contact_create, contact_edit, contact_delete

app_name = "contacts"

urlpatterns = [
    path("", contact_list, name="list"),
    path("new/", contact_create, name="create"),
    path("<uuid:pk>/", contact_detail, name="detail"),
    path("<uuid:pk>/edit/", contact_edit, name="edit"),
    path("<uuid:pk>/delete/", contact_delete, name="delete"),
]
