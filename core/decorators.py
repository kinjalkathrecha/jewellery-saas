import time
import functools
import logging
from django.core.cache import cache
from django.http import JsonResponse, HttpResponse

logger = logging.getLogger(__name__)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip

def redis_rate_limit(key_prefix, limit, period, limit_by='ip'):
    """
    Custom decorator to enforce rate limits via Redis (or fallback cache backend).

    Arguments:
    - key_prefix: String identifier for the rate limit (e.g. 'login', 'barcode')
    - limit: Maximum requests allowed in the time window
    - period: The time window in seconds (e.g. 60 for minutes, 3600 for hours)
    - limit_by: 'ip' (rate limit by client IP) or 'shop' (rate limit by shop ID)
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if limit_by == 'shop':
                identifier = str(request.shop.id) if hasattr(request, 'shop') and request.shop else 'anonymous'
            else:
                identifier = get_client_ip(request)

            # Construct the rate limit key
            key = f"ratelimit:{key_prefix}:{identifier}"

            try:
                current_hits = cache.get(key)
                if current_hits is None:
                    # Key does not exist, initialize it
                    cache.set(key, 1, period)
                    current_hits = 1
                else:
                    # Increment the counter
                    try:
                        current_hits = cache.incr(key)
                    except ValueError:
                        # Fallback if cache backend fails to increment atomically
                        current_hits += 1
                        cache.set(key, current_hits, period)

                if current_hits > limit:
                    logger.warning(
                        f"[Rate Limit Exceeded] Prefix: {key_prefix}, Identifier: {identifier}, "
                        f"Hits: {current_hits}/{limit} in {period}s."
                    )
                    # If this is an API request (starts with /api/ or has JSON accept headers), return JSON
                    if request.path.startswith('/api/') or 'application/json' in request.META.get('HTTP_ACCEPT', ''):
                        return JsonResponse(
                            {"error": "Too many requests. Please try again later."},
                            status=429
                        )
                    else:
                        response = HttpResponse(
                            "<h1>429 Too Many Requests</h1><p>You have exceeded your rate limit. Please try again later.</p>",
                            status=429
                        )
                        response['Retry-After'] = str(period)
                        return response
            except Exception as e:
                # Fail open to prevent redis connection failure from blocking user access
                logger.error(f"[Rate Limit Error] Failed to enforce rate limit: {e}")

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
