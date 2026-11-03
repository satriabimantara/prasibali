from django.conf import settings


class SecurityHeadersMiddleware:
    """Content-Security-Policy and Permissions-Policy (production). Django 5.2 has no built-in CSP setting.

    The values come from settings.CONTENT_SECURITY_POLICY and settings.PERMISSIONS_POLICY; an empty value adds nothing.
    A header a view set itself is kept.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.headers = {
            name: value
            for name, value in (
                ("Content-Security-Policy", getattr(settings, "CONTENT_SECURITY_POLICY", "")),
                ("Permissions-Policy", getattr(settings, "PERMISSIONS_POLICY", "")),
            )
            if value
        }

    def __call__(self, request):
        response = self.get_response(request)
        for name, value in self.headers.items():
            response.headers.setdefault(name, value)
        return response
