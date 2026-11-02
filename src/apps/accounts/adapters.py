from allauth.account import app_settings as allauth_settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context as allauth_context
from allauth.utils import build_absolute_uri
from django.urls import reverse


class AccountAdapter(DefaultAccountAdapter):
    """Adds the values our email templates need (sign-in link, link lifetime)."""

    def send_mail(self, template_prefix, email, context):
        request = allauth_context.request
        context = {
            "login_url": build_absolute_uri(request, reverse("account_login")),
            "confirmation_expire_days": allauth_settings.EMAIL_CONFIRMATION_EXPIRE_DAYS,
            **context,
        }
        super().send_mail(template_prefix, email, context)
