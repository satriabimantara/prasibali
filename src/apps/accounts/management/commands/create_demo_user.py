"""Create or update the demo account for the competition judges.

Credentials come from DEMO_USER_EMAIL and DEMO_USER_PASSWORD in the environment; they never live in the repo.
Running it again updates the password and keeps the email verified (idempotent).
"""

import os

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import PRIVACY_POLICY_VERSION


class Command(BaseCommand):
    help = "Create or update the demo user from DEMO_USER_EMAIL and DEMO_USER_PASSWORD (email marked verified)."

    def handle(self, *args, **options):
        email = os.environ.get("DEMO_USER_EMAIL", "").strip().lower()
        password = os.environ.get("DEMO_USER_PASSWORD", "")
        if not email or not password:
            raise CommandError("Set DEMO_USER_EMAIL and DEMO_USER_PASSWORD in the environment (.env) first.")

        User = get_user_model()
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"full_name": "Demo PrasiBali", "role": User.Role.GENERAL},
            )
            user.set_password(password)
            user.is_active = True
            if not user.privacy_accepted_at:
                user.privacy_accepted_at = timezone.now()
                user.privacy_policy_version = PRIVACY_POLICY_VERSION
            user.save()

            EmailAddress.objects.filter(user=user).exclude(email__iexact=email).update(primary=False)
            address, _ = EmailAddress.objects.get_or_create(user=user, email=email)
            address.verified = True
            address.primary = True
            address.save()

        # Never print the password.
        self.stdout.write(self.style.SUCCESS(f"Demo user {'created' if created else 'updated'}: {email}"))
