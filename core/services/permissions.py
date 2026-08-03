from django.utils import timezone

from accounts.models import CustomUser
from billing.models import Invoice
from inventory.models import JewelleryItem


class PlanPermissionService:
    @staticmethod
    def check(shop, action):
        """
        Centrally verifies if a shop has permission to perform a write action
        based on active subscription status and feature usage limits.
        """
        if not shop:
            return False
            
        status_info = shop.get_subscription_status()
        
        # If the subscription is completely locked out (past trial or grace period)
        if status_info['is_locked']:
            return False
            
        sub = shop.active_subscription
        if not sub:
            return False

        if action == 'create_product':
            current_count = JewelleryItem.objects.filter(shop=shop).count()
            return current_count < sub.max_products

        elif action == 'add_staff':
            current_count = CustomUser.objects.filter(shop=shop).count()
            return current_count < sub.max_users

        elif action == 'create_invoice':
            now = timezone.now()
            # Count invoices created during this calendar month
            current_month_count = Invoice.objects.filter(
                shop=shop,
                created_at__year=now.year,
                created_at__month=now.month
            ).count()
            return current_month_count < sub.max_invoices_per_month
            
        # General active feature blocks (allowed if subscription is active and not locked)
        elif action in ['create_repair', 'create_customer', 'print_tags', 'update_rates']:
            return True

        return False
