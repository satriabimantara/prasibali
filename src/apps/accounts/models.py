from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

# Bump when the privacy policy text changes; stored with each consent.
PRIVACY_POLICY_VERSION = "2026-11-03"


class UserManager(BaseUserManager):
    """Manager for an email-only user model (no username)."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["is_staff"] is not True or extra_fields["is_superuser"] is not True:
            raise ValueError("A superuser must have is_staff=True and is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Email-based account with the profile fields PrasiBali.ai needs."""

    class Role(models.TextChoices):
        STUDENT = "student", _("Student")
        TEACHER = "teacher", _("Teacher")
        RESEARCHER = "researcher", _("Researcher")
        GENERAL = "general", _("General public")

    username = None
    first_name = None
    last_name = None

    email = models.EmailField(_("email address"), unique=True)
    # Required by the signup and profile forms; blank here so createsuperuser works without it.
    full_name = models.CharField(_("full name"), max_length=150, blank=True)
    institution = models.CharField(_("institution"), max_length=200, blank=True)
    role = models.CharField(_("role"), max_length=20, choices=Role.choices, default=Role.GENERAL)
    language = models.CharField(
        _("preferred language"), max_length=8, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE
    )
    privacy_accepted_at = models.DateTimeField(_("privacy policy accepted at"), null=True, blank=True)
    privacy_policy_version = models.CharField(_("privacy policy version"), max_length=20, blank=True)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.full_name.strip()

    def get_short_name(self):
        return self.get_full_name().split(" ")[0] if self.full_name else self.email
