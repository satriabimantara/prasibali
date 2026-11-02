from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("healthz", views.healthz, name="healthz"),
]
