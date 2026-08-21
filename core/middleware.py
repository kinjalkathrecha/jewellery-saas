import threading
import uuid

from django.utils.deprecation import MiddlewareMixin

_thread_locals = threading.local()


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


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
            else:
                # User has no shop (e.g. Django superuser / staff or orphan user)
                path = request.path
                tenant_prefixes = ("/dashboard/", "/inventory/", "/billing/", "/customers/", "/repairs/", "/barcodes/")
                if path.startswith(tenant_prefixes):
                    if request.user.is_superuser or request.user.is_staff:
                        from django.shortcuts import redirect

                        return redirect("admin:index")
                    from django.http import HttpResponseForbidden

                    return HttpResponseForbidden(
                        "Access Denied: You are not associated with any shop. Please contact the administrator."
                    )

        # Store user and IP in thread locals for generic auditing
        _thread_locals.user = request.user if hasattr(request, "user") else None
        _thread_locals.ip_address = get_client_ip(request)

    def process_response(self, request, response):
        if hasattr(_thread_locals, "user"):
            del _thread_locals.user
        if hasattr(_thread_locals, "ip_address"):
            del _thread_locals.ip_address
        return response


def get_current_request_id():
    """
    Retrieve the current request's unique correlation ID from thread-local storage.
    """
    return getattr(_thread_locals, "request_id", None)


def get_current_user():
    """
    Retrieve the current request's authenticated user from thread-local storage.
    """
    return getattr(_thread_locals, "user", None)


def get_current_ip():
    """
    Retrieve the current request's IP address from thread-local storage.
    """
    return getattr(_thread_locals, "ip_address", None)


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
