from unittest import mock

import pytest
from django.db import OperationalError
from django.urls import reverse


@pytest.mark.django_db
def test_healthz_ok(client):
    response = client.get(reverse("pages:healthz"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert "no-cache" in response["Cache-Control"]


def test_healthz_reports_database_failure(client):
    with mock.patch("apps.pages.views.connection") as connection:
        connection.cursor.side_effect = OperationalError("db down")
        response = client.get("/healthz")

    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"


def test_healthz_only_allows_get(client):
    assert client.post("/healthz").status_code == 405
