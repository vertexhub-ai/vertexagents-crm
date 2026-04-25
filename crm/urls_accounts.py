from django.urls import path
from crm.views.accounts import account_list, account_detail, account_create, account_edit, account_delete

app_name = "accounts"

urlpatterns = [
    path("", account_list, name="list"),
    path("new/", account_create, name="create"),
    path("<uuid:pk>/", account_detail, name="detail"),
    path("<uuid:pk>/edit/", account_edit, name="edit"),
    path("<uuid:pk>/delete/", account_delete, name="delete"),
]
