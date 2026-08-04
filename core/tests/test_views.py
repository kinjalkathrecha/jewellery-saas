from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse


@pytest.mark.django_db
@patch("django.core.cache.cache.get")
@patch("django.core.cache.cache.set")
@patch("django.core.files.storage.default_storage.save")
@patch("django.core.files.storage.default_storage.exists")
@patch("django.core.files.storage.default_storage.delete")
@patch("core.views.current_app.control.inspect")
def test_health_check_success(mock_celery_inspect, mock_delete, mock_exists, mock_save, mock_set, mock_get, client):
    """
    Test that when all backends (DB, Redis, Celery, Storage) are functional,
    the endpoint returns 200 and 'healthy' status.
    """
    mock_get.return_value = "ok"
    mock_exists.return_value = True

    # Mock celery inspect ping
    mock_inspect = MagicMock()
    mock_inspect.ping.return_value = {"worker1": "pong"}
    mock_celery_inspect.return_value = mock_inspect

    url = reverse("health_check")
    response = client.get(url)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["database"] == "ok"
    assert data["redis"] == "ok"
    assert data["celery"] == "ok"
    assert data["storage"] == "ok"
    assert data["version"] == "0.96"
    assert "timestamp" in data
    assert "metrics" in data
    assert data["metrics"]["active_celery_workers"] == 1


@pytest.mark.django_db
@patch("core.views.connection.cursor")
@patch("django.core.cache.cache.get")
@patch("django.core.cache.cache.set")
@patch("django.core.files.storage.default_storage.save")
@patch("django.core.files.storage.default_storage.exists")
@patch("django.core.files.storage.default_storage.delete")
@patch("core.views.current_app.control.inspect")
def test_health_check_failure(
    mock_celery_inspect, mock_delete, mock_exists, mock_save, mock_set, mock_get, mock_cursor, client
):
    """
    Test that if one of the critical services (e.g. database) fails,
    the endpoint returns 503 and 'unhealthy' status.
    """
    from django.db import connections
    from django.db.backends.base.base import BaseDatabaseWrapper

    real_conn = connections["default"]
    real_cursor_func = BaseDatabaseWrapper.cursor

    def mock_cursor_side_effect(*args, **kwargs):
        cursor = real_cursor_func(real_conn, *args, **kwargs)
        real_execute = cursor.execute

        def mock_execute(sql, params=None):
            if sql == "SELECT 1":
                raise Exception("Database is down")
            return real_execute(sql, params)

        cursor.execute = mock_execute
        return cursor

    mock_cursor.side_effect = mock_cursor_side_effect

    mock_get.return_value = "ok"
    mock_exists.return_value = True

    # Mock celery inspect to return None (no workers)
    mock_inspect = MagicMock()
    mock_inspect.ping.return_value = None
    mock_celery_inspect.return_value = mock_inspect

    url = reverse("health_check")
    response = client.get(url)

    assert response.status_code == 503
    data = response.json()

    assert data["status"] == "unhealthy"
    assert "Database is down" in data["database"]
