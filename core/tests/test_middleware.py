import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_correlation_id_middleware(client):
    url = reverse("accounts:login")
    response = client.get(url)
    assert response.status_code == 200
    assert "X-Correlation-ID" in response
    assert len(response["X-Correlation-ID"]) > 10 # UUID length check
