from celery import current_app
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone


def health_check(request):
    """
    A detailed health check endpoint returning the status of database connectivity,
    Redis cache, Celery, and local storage, along with version, timestamps and extensible operational metrics.
    """
    database_ok = "error"
    redis_ok = "error"
    celery_ok = "error"
    storage_ok = "error"
    active_workers = 0

    # 1. Probe Database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database_ok = "ok"
    except Exception as e:
        database_ok = f"error: {e!s}"

    # 2. Probe Redis
    try:
        cache.set("health_probe_key", "ok", 10)
        if cache.get("health_probe_key") == "ok":
            redis_ok = "ok"
    except Exception as e:
        redis_ok = f"error: {e!s}"

    # 3. Probe Celery
    try:
        # Run inspect with short timeout to prevent hanging the HTTP thread
        inspect = current_app.control.inspect(timeout=1.0)
        ping_res = inspect.ping()
        if ping_res:
            celery_ok = "ok"
            active_workers = len(ping_res)
        else:
            celery_ok = "no_workers"
    except Exception as e:
        celery_ok = f"error: {e!s}"

    # 4. Probe Storage
    try:
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        test_file_path = "health_probe_test.txt"
        default_storage.save(test_file_path, ContentFile(b"ok"))
        if default_storage.exists(test_file_path):
            default_storage.delete(test_file_path)
            storage_ok = "ok"
    except Exception as e:
        storage_ok = f"error: {e!s}"

    # Determine overall status
    is_healthy = (
        database_ok == "ok" and
        redis_ok == "ok" and
        (celery_ok == "ok" or celery_ok == "no_workers") and
        storage_ok == "ok"
    )

    # Expose operational metrics (prepared for Prometheus/monitoring hooks)
    metrics = {
        "active_celery_workers": active_workers,
        "pending_tasks": 0,                 # Extensible: query queue lengths later
        "redis_memory_usage_bytes": 0,       # Extensible: query Redis INFO memory later
        "cache_hit_ratio": 1.0,             # Extensible: query hit ratios later
        "database_connections": 1           # Extensible: query active connections count later
    }

    # Fetch app version from settings
    app_version = getattr(settings, "APP_VERSION", "0.96")

    response_data = {
        "status": "healthy" if is_healthy else "unhealthy",
        "database": database_ok,
        "redis": redis_ok,
        "celery": celery_ok,
        "storage": storage_ok,
        "version": app_version,
        "timestamp": timezone.now().isoformat(),
        "metrics": metrics,
    }

    status_code = 200 if is_healthy else 503
    return JsonResponse(response_data, status=status_code)

