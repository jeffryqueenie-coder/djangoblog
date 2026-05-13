from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseNotFound


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
        '/robot/',
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
    rate_limit_window = 60
    rate_limit_max_requests = 180

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, 'PUBLIC_READ_ONLY_MODE', True):
            path = request.path_info
            if request.method.upper() not in self.allowed_methods:
                return HttpResponseNotFound()
            if path in self.blocked_exact_paths or any(path.startswith(prefix) for prefix in self.blocked_prefixes):
                return HttpResponseNotFound()
            if self._is_rate_limited(request):
                return HttpResponse('Too Many Requests', status=429)
        return self.get_response(request)

    def _is_rate_limited(self, request):
        max_requests = int(getattr(settings, 'PUBLIC_RATE_LIMIT_PER_MINUTE', self.rate_limit_max_requests))
        if max_requests <= 0:
            return False

        ip = self._client_ip(request)
        key = f'public-read-only-rate:{ip}'
        current = cache.get(key)
        if current is None:
            cache.set(key, 1, self.rate_limit_window)
            return False
        if current >= max_requests:
            return True
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, self.rate_limit_window)
        return False

    @staticmethod
    def _client_ip(request):
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
