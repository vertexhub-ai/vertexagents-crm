from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from accounts.views import dashboard

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("password_reset/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "password_reset/confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("password_reset/complete/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("", dashboard, name="dashboard"),
]
