"""Session 7: security headers middleware, JSON log formatter, error pages, no inline scripts."""

import json
import logging
import re
import sys
from pathlib import Path

import pytest
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.urls import path

from apps.pages.middleware import SecurityHeadersMiddleware
from config.jsonlog import JsonFormatter

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "src" / "templates"


@override_settings(CONTENT_SECURITY_POLICY="default-src 'self'", PERMISSIONS_POLICY="camera=()")
def test_security_headers_middleware_adds_headers():
    middleware = SecurityHeadersMiddleware(lambda request: HttpResponse("ok"))
    response = middleware(RequestFactory().get("/"))
    assert response["Content-Security-Policy"] == "default-src 'self'"
    assert response["Permissions-Policy"] == "camera=()"


@override_settings(CONTENT_SECURITY_POLICY="", PERMISSIONS_POLICY="")
def test_security_headers_middleware_without_values_adds_nothing():
    response = SecurityHeadersMiddleware(lambda request: HttpResponse("ok"))(RequestFactory().get("/"))
    assert "Content-Security-Policy" not in response and "Permissions-Policy" not in response


def test_json_formatter_writes_one_json_object():
    request = RequestFactory().post("/analisis/")
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.getLogger("django.request").makeRecord(
            "django.request", logging.ERROR, __file__, 1, "Internal Server Error: %s", ("/analisis/",),
            sys.exc_info(), extra={"status_code": 500, "request": request},
        )
    line = JsonFormatter().format(record)
    data = json.loads(line)
    assert "\n" not in line.strip() or line.count("{") >= 1
    assert data["level"] == "ERROR" and data["logger"] == "django.request"
    assert data["message"] == "Internal Server Error: /analisis/"
    assert data["status_code"] == 500 and data["method"] == "POST" and data["path"] == "/analisis/"
    assert "ValueError: boom" in data["exc_info"]


def test_templates_have_no_inline_scripts():
    """The production CSP has no 'unsafe-inline' for scripts: every <script> must load a file or carry JSON data."""
    offenders = []
    for template in TEMPLATES_DIR.rglob("*.html"):
        for tag in re.findall(r"<script\b[^>]*>", template.read_text(encoding="utf-8")):
            if "src=" not in tag and "application/json" not in tag:
                offenders.append(f"{template.name}: {tag}")
    assert offenders == []


# --------------------------------------------------------------------------- error pages
def _boom(request):
    raise RuntimeError("test failure")


urlpatterns = [path("boom/", _boom)]


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_404_page(client):
    response = client.get("/tidak-ada-halaman-ini/")
    html = response.content.decode()
    assert response.status_code == 404
    assert "Halaman tidak ditemukan" in html and 'id="main"' in html


@override_settings(DEBUG=False, ROOT_URLCONF=__name__)
def test_500_page(client):
    client.raise_request_exception = False
    response = client.get("/boom/")
    html = response.content.decode()
    assert response.status_code == 500
    assert "Terjadi kesalahan" in html and "css/app.css" in html
