from allauth.account import views as allauth_views
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("apps.accounts.urls")),
    path("akun/", include("allauth.urls")),  # verification, password reset, logout, email/password change
    # Indonesian entry points for allauth. They come after allauth.urls on purpose: when several patterns
    # share a name, reverse() returns the last one, so "account_login" -> /masuk/, "account_signup" -> /daftar/.
    path("masuk/", allauth_views.login, name="account_login"),
    path("daftar/", allauth_views.signup, name="account_signup"),
    path("", include("apps.pages.urls")),
    path("admin/", admin.site.urls),
]
