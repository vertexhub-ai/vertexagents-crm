from django.urls import path

from . import views

app_name = "leads"

urlpatterns = [
    path("", views.lead_list, name="list"),
    path("new/", views.lead_create, name="create"),
    path("<uuid:pk>/", views.lead_detail, name="detail"),
    path("<uuid:pk>/edit/", views.lead_edit, name="edit"),
    path("<uuid:pk>/disqualify/", views.lead_disqualify, name="disqualify"),
    path("<uuid:pk>/delete/", views.lead_delete, name="delete"),
]
