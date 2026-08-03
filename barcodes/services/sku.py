from django.db import transaction

from core.models import Shop


def generate_next_sku(shop_id):
    """
    Generates a sequential, meaningful SKU for a shop in a thread-safe,
    concurrency-safe manner using select_for_update().
    """
    with transaction.atomic():
        shop = Shop.objects.select_for_update().get(id=shop_id)
        seq = shop.next_sku_number

        # Increment shop SKU pointer
        shop.next_sku_number = seq + 1
        shop.save(update_fields=["next_sku_number"])

        # Calculate prefix
        if shop.sku_prefix:
            prefix = "".join(c for c in shop.sku_prefix if c.isalnum()).upper()
        else:
            words = [w for w in shop.name.split() if w.isalnum()]
            if len(words) >= 2:
                prefix = "".join([w[0] for w in words]).upper()
            elif len(words) == 1:
                prefix = words[0][:3].upper()
            else:
                prefix = "JWL"
            prefix = "".join(c for c in prefix if c.isalnum())

        return f"{prefix}-{seq:06d}"
