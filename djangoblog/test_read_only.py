from django.http import HttpResponse
from django.core.cache import cache
from django.test import Client, RequestFactory, SimpleTestCase, override_settings

from djangoblog.read_only import PublicReadOnlyMiddleware


@override_settings(PUBLIC_READ_ONLY_MODE=True)
class PublicReadOnlyModeTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.middleware = PublicReadOnlyMiddleware(lambda request: HttpResponse('ok'))

    def test_sensitive_public_routes_return_404(self):
        blocked_paths = (
            '/admin',
            '/admin/',
            '/login',
            '/login/',
            '/logout/',
            '/register/',
            '/forget_password/',
            '/forget_password_code/',
            '/account/result.html',
            '/oauth/oauthlogin',
            '/mdeditor/uploads/',
            '/owntracks/show_dates',
            '/robot',
            '/clean',
            '/upload',
        )

        for path in blocked_paths:
            with self.subTest(path=path):
                request = self.factory.get(path)
                response = self.middleware(request)
                self.assertEqual(response.status_code, 404)

    def test_state_changing_methods_return_404(self):
        for method in ('post', 'put', 'patch', 'delete', 'options'):
            with self.subTest(method=method):
                request = getattr(self.factory, method)('/')
                response = self.middleware(request)
                self.assertEqual(response.status_code, 404)

    def test_public_get_routes_pass_through(self):
        for path in ('/', '/news/', '/search?q=python', '/rss/', '/sitemap.xml', '/health/'):
            with self.subTest(path=path):
                request = self.factory.get(path)
                response = self.middleware(request)
                self.assertEqual(response.status_code, 200)

    @override_settings(PUBLIC_READ_ONLY_MODE=False)
    def test_middleware_can_be_disabled(self):
        request = self.factory.post('/login/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_django_client_receives_direct_404(self):
        client = Client()

        for path in ('/admin/', '/login/', '/oauth/oauthlogin', '/owntracks/show_dates'):
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.content, b'')

    @override_settings(PUBLIC_RATE_LIMIT_PER_MINUTE=2)
    def test_rate_limit_returns_429(self):
        first = self.middleware(self.factory.get('/'))
        second = self.middleware(self.factory.get('/'))
        third = self.middleware(self.factory.get('/'))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 429)

    def test_robots_txt_is_public(self):
        response = Client().get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sitemap: http://testserver/sitemap.xml')
        self.assertContains(response, 'Disallow: /admin')
