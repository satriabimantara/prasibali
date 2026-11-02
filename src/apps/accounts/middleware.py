from django.conf import settings
from django.utils import translation

LANGUAGE_CODES = {code for code, _name in settings.LANGUAGES}


class UserLanguageMiddleware:
    """Use the signed-in user's preferred language and keep it in the language cookie.

    Runs after AuthenticationMiddleware, so it overrides what LocaleMiddleware picked from the
    cookie or Accept-Language. The cookie keeps the choice after logout.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = _user_language(request)
        if language:
            translation.activate(language)
            request.LANGUAGE_CODE = language

        response = self.get_response(request)

        # Re-read: the view may have changed the preference (profile form) or signed the user out.
        language = _user_language(request)
        cookie = settings.LANGUAGE_COOKIE_NAME
        if language and request.COOKIES.get(cookie) != language and cookie not in response.cookies:
            set_language_cookie(response, language)
        return response


def _user_language(request):
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and user.language in LANGUAGE_CODES:
        return user.language
    return None


def set_language_cookie(response, language):
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        language,
        max_age=settings.LANGUAGE_COOKIE_AGE,
        path=settings.LANGUAGE_COOKIE_PATH,
        domain=settings.LANGUAGE_COOKIE_DOMAIN,
        secure=settings.LANGUAGE_COOKIE_SECURE,
        httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
    )
