from allauth.account.decorators import verified_email_required
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST
from django.views.i18n import set_language as django_set_language

from .forms import DeleteAccountForm, ProfileForm
from .middleware import LANGUAGE_CODES, set_language_cookie


@verified_email_required
@require_http_methods(["GET", "POST"])
def profile(request):
    user = request.user
    form = ProfileForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        form.save()
        translation.activate(user.language)
        messages.success(request, _("Your profile has been saved."))
        response = redirect("accounts:profile")
        set_language_cookie(response, user.language)
        return response
    return render(request, "accounts/profile.html", {"form": form})


@verified_email_required
@require_http_methods(["GET", "POST"])
def delete_account(request):
    user = request.user
    form = DeleteAccountForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        logout(request)
        user.delete()  # cascades to the user's analysis history
        messages.success(request, _("Your account and all of its data have been deleted."))
        return redirect(settings.LOGIN_URL)
    return render(request, "accounts/delete_account.html", {"form": form})


@require_POST
def set_language(request):
    """Django's set_language, which also stores the choice on the signed-in user's profile."""
    language = request.POST.get("language")
    if request.user.is_authenticated and language in LANGUAGE_CODES and request.user.language != language:
        request.user.language = language
        request.user.save(update_fields=["language"])
    return django_set_language(request)
