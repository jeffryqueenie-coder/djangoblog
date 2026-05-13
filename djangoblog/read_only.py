from django.conf import settings
from django.http import HttpResponseNotFound


class PublicReadOnlyMiddleware:
    """Expose only public browsing endpoints when the site runs in read-only mode."""

    blocked_prefixes = (
        '/admin/',
        '/login/',
        '/logout/',
        '/register/',
        '/forget_password/',
        '/forget_password_code/',
        '/account/',
        '/oauth/',
        '/mdeditor/',
        '/owntracks/',
        '/robot',
    )
    blocked_exact_paths = (
        '/admin',
        '/login',
        '/logout',
        '/register',
        '/forget_password',
        '/forget_password_code',
        '/account',
        '/oauth',
        '/mdeditor',
        '/owntracks',
        '/robot',
        '/clean',
        '/upload',
    )
    allowed_methods = {'GET', 'HEAD'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, 'PUBLIC_READ_ONLY_MODE', True):
            path = request.path_info
            if request.method.upper() not in self.allowed_methods:
                return HttpResponseNotFound()
            if path in self.blocked_exact_paths or any(path.startswith(prefix) for prefix in self.blocked_prefixes):
                return HttpResponseNotFound()
        return self.get_response(request)
