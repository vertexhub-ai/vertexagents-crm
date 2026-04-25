from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.account_list, name="list"),
    path("new/", views.account_create, name="create"),
    path("<uuid:pk>/", views.account_detail, name="detail"),
    path("<uuid:pk>/edit/", views.account_edit, name="edit"),
    path("<uuid:pk>/delete/", views.account_delete, name="delete"),
]
