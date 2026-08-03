from django.utils.deprecation import MiddlewareMixin


class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.shop = None
        request.subscription_status = None
        request.subscription_active = True
        request.subscription_locked = False
        request.subscription_message = ""

        if request.user.is_authenticated:
            if hasattr(request.user, 'shop') and request.user.shop:
                request.shop = request.user.shop
                
                # Resolve active status details
                status_info = request.shop.get_subscription_status()
                request.subscription_status = status_info
                request.subscription_active = status_info['active']
                request.subscription_locked = status_info['is_locked']
                request.subscription_message = status_info['message']
