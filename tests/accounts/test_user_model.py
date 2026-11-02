import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError


def test_email_is_the_username_field():
    User = get_user_model()
    assert User.USERNAME_FIELD == "email"
    assert User.REQUIRED_FIELDS == []
    field_names = {field.name for field in User._meta.get_fields()}
    assert "username" not in field_names
    assert {"full_name", "institution", "role", "language", "privacy_accepted_at"} <= field_names


@pytest.mark.django_db
def test_create_user_normalises_email():
    user = get_user_model().objects.create_user(email="Wayan@Example.COM", password="x-Secret-123")

    assert user.email == "wayan@example.com"
    assert user.check_password("x-Secret-123")
    assert not user.is_staff
    assert user.language == "id"
    assert str(user) == "wayan@example.com"


@pytest.mark.django_db
def test_email_is_unique():
    User = get_user_model()
    User.objects.create_user(email="nyoman@example.com", password="x")
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="NYOMAN@example.com", password="x")


@pytest.mark.django_db
def test_create_superuser():
    user = get_user_model().objects.create_superuser(email="admin@example.com", password="x")

    assert user.is_staff and user.is_superuser


def test_create_user_requires_email():
    with pytest.raises(ValueError, match="email"):
        get_user_model().objects.create_user(email="", password="x")


def test_full_name_helpers():
    user = get_user_model()(email="luh@example.com", full_name="Luh Sari Dewi")

    assert user.get_full_name() == "Luh Sari Dewi"
    assert user.get_short_name() == "Luh"
