from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings


class LoginRequiredMiddleware:
    _EXEMPT = ("/login/", "/static/", "/admin/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path
            if not any(path.startswith(p) for p in self._EXEMPT):
                if path.startswith("/api/"):
                    return JsonResponse({"error": "Authentication required"}, status=401)
                return redirect(f"{settings.LOGIN_URL}?next={path}")
        return self.get_response(request)
