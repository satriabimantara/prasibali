from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("akun/profil/", views.profile, name="profile"),
    path("akun/hapus/", views.delete_account, name="delete"),
    path("bahasa/", views.set_language, name="set_language"),
]
