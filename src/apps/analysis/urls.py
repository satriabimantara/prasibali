from django.urls import path

from . import views

app_name = "analysis"

urlpatterns = [
    path("analisis/", views.workspace, name="workspace"),
    path("riwayat/", views.history_list, name="history"),
    path("riwayat/hapus-semua/", views.history_delete_all, name="history_delete_all"),
    path("riwayat/<uuid:run_id>/", views.history_detail, name="history_detail"),
    path("riwayat/<uuid:run_id>/hapus/", views.history_delete, name="history_delete"),
]
