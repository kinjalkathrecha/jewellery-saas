import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache Timeout Constants (in seconds)
TIMEOUT_DASHBOARD = 600  # 10 minutes
TIMEOUT_METALRATE = 300  # 5 minutes
TIMEOUT_SUBSCRIPTION = 60  # 1 minute
TIMEOUT_INVOICE = 3600  # 1 hour


# Key Builders
def get_dashboard_key(shop_id):
    return f"shop:{shop_id}:dashboard"


def get_subscription_key(shop_id):
    return f"shop:{shop_id}:subscription"


def get_metal_rate_key(shop_id, metal_type):
    return f"shop:{shop_id}:metalrate:{metal_type.lower()}"


def get_invoice_key(invoice_id):
    return f"invoice:{invoice_id}"


# Operations & Invalidation Helpers
def set_dashboard_stats(shop_id, data):
    key = get_dashboard_key(shop_id)
    cache.set(key, data, TIMEOUT_DASHBOARD)
    logger.debug(f"[Cache Service] Set dashboard cache for shop {shop_id}.")


def get_dashboard_stats(shop_id):
    key = get_dashboard_key(shop_id)
    return cache.get(key)


def invalidate_dashboard(shop_id):
    key = get_dashboard_key(shop_id)
    cache.delete(key)
    logger.info(f"[Cache Service] Invalidated dashboard cache for shop {shop_id}.")


def set_subscription_status(shop_id, data):
    key = get_subscription_key(shop_id)
    cache.set(key, data, TIMEOUT_SUBSCRIPTION)
    logger.debug(f"[Cache Service] Set subscription cache for shop {shop_id}.")


def get_subscription_status(shop_id):
    key = get_subscription_key(shop_id)
    return cache.get(key)


def invalidate_subscription(shop_id):
    key = get_subscription_key(shop_id)
    cache.delete(key)
    logger.info(f"[Cache Service] Invalidated subscription cache for shop {shop_id}.")


def set_metal_rate(shop_id, metal_type, rate):
    key = get_metal_rate_key(shop_id, metal_type)
    cache.set(key, rate, TIMEOUT_METALRATE)
    logger.debug(f"[Cache Service] Set metal rate cache for shop {shop_id}, type {metal_type}.")


def get_metal_rate(shop_id, metal_type):
    key = get_metal_rate_key(shop_id, metal_type)
    return cache.get(key)


def invalidate_rates(shop_id, metal_type=None):
    if metal_type:
        key = get_metal_rate_key(shop_id, metal_type)
        cache.delete(key)
        logger.info(f"[Cache Service] Invalidated metal rate cache for shop {shop_id}, type {metal_type}.")
    else:
        # Invalidate standard gold and silver keys if metal_type is unspecified
        cache.delete(get_metal_rate_key(shop_id, "gold"))
        cache.delete(get_metal_rate_key(shop_id, "silver"))
        logger.info(f"[Cache Service] Invalidated all metal rate caches for shop {shop_id}.")


def set_invoice(invoice_id, data):
    key = get_invoice_key(invoice_id)
    cache.set(key, data, TIMEOUT_INVOICE)


def get_invoice(invoice_id):
    key = get_invoice_key(invoice_id)
    return cache.get(key)


def invalidate_invoice(invoice_id):
    key = get_invoice_key(invoice_id)
    cache.delete(key)
    logger.info(f"[Cache Service] Invalidated invoice cache for invoice {invoice_id}.")
