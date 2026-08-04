import pytest
from django.core.cache import cache
from django.urls import reverse

@pytest.mark.django_db
class TestRateLimiting:
    def setup_method(self):
        cache.clear()

    def test_login_rate_limiting(self, client):
        url = reverse("accounts:login")

        # 5 hits are allowed
        for i in range(5):
            response = client.get(url)
            assert response.status_code == 200

        # 6th hit must be blocked with HTTP 429
        response = client.get(url)
        assert response.status_code == 429
        assert "Retry-After" in response

    def test_password_reset_rate_limiting(self, client):
        url = reverse("accounts:password_reset")

        # 3 hits are allowed
        for i in range(3):
            response = client.get(url)
            assert response.status_code == 200

        # 4th hit must be blocked with HTTP 429
        response = client.get(url)
        assert response.status_code == 429
