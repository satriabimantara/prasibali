from django.urls import path

from . import views

app_name = "analysis"

urlpatterns = [
    path("analisis/", views.workspace, name="workspace"),
]
