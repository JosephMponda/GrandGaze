from django.core.exceptions import PermissionDenied
from django.shortcuts import render


class PermissionDeniedMiddleware:
    """Catches PermissionDenied before Django's WSGI handler generates a
    traceback page. Renders the custom 403.html instead, even in DEBUG mode."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):
            return render(request, "403.html", status=403)
        return None
