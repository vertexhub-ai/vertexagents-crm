from django.urls import path

from . import views

urlpatterns = [
    path('leads/', views.lead_list, name='lead_list'),
    path('leads/<uuid:pk>/', views.lead_detail, name='lead_detail'),
    path('leads/<uuid:pk>/convert/', views.lead_convert, name='lead_convert'),
]
