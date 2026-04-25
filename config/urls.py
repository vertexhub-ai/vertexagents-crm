from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/login/", auth_views.LoginView.as_view(template_name="auth/login.html"), name="login"),
    path("auth/logout/", auth_views.LogoutView.as_view(), name="logout"),
    # app_name set inside each urls_* module provides the namespace
    path("accounts/", include("crm.urls_accounts")),
    path("contacts/", include("crm.urls_contacts")),
    path("", RedirectView.as_view(url="/contacts/", permanent=False)),
]
