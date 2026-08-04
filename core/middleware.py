from django.utils.deprecation import MiddlewareMixin


class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.shop = None
        request.subscription_status = None
        request.subscription_active = True
        request.subscription_locked = False
        request.subscription_message = ""

        if request.user.is_authenticated:
            if hasattr(request.user, "shop") and request.user.shop:
                request.shop = request.user.shop

                # Resolve active status details
                status_info = request.shop.get_subscription_status()
                request.subscription_status = status_info
                request.subscription_active = status_info["active"]
                request.subscription_locked = status_info["is_locked"]
                request.subscription_message = status_info["message"]


import threading
import uuid

_thread_locals = threading.local()

def get_current_request_id():
    """
    Retrieve the current request's unique correlation ID from thread-local storage.
    """
    return getattr(_thread_locals, "request_id", None)

class CorrelationIdMiddleware(MiddlewareMixin):
    """
    Middleware that ensures every request has a unique correlation ID.
    If one is passed in headers from Nginx (X-Correlation-ID), it uses it;
    otherwise it generates a fresh UUID.
    """
    def process_request(self, request):
        correlation_id = request.META.get("HTTP_X_CORRELATION_ID") or request.META.get("HTTP_X_REQUEST_ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        request.request_id = correlation_id
        _thread_locals.request_id = correlation_id

    def process_response(self, request, response):
        if hasattr(request, "request_id"):
            response["X-Correlation-ID"] = request.request_id
        if hasattr(_thread_locals, "request_id"):
            del _thread_locals.request_id
        return response

