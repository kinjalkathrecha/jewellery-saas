from django.db import transaction

from barcodes.services.barcode import generate_barcode_svg
from barcodes.services.sku import generate_next_sku
from inventory.models import JewelleryItem


def create_jewellery_item(shop, data, image_file=None):
    """
    Service to explicitly create a JewelleryItem.
    Locks counter, generates next SKU if empty, creates barcode, and saves under a transaction.
    """
    with transaction.atomic():
        item = JewelleryItem(shop=shop)

        # Standard model fields mapping
        for field in [
            "item_name",
            "category",
            "metal_type",
            "weight_in_grams",
            "making_charges",
            "profit_margin",
            "price",
            "stock_quantity",
        ]:
            if field in data:
                setattr(item, field, data[field])

        # Support optional values
        if data.get("design_code"):
            item.design_code = data["design_code"]
        else:
            item.design_code = generate_next_sku(shop.id)

        if data.get("barcode_type"):
            item.barcode_type = data["barcode_type"]

        if image_file:
            item.image = image_file
        elif "image" in data:
            item.image = data["image"]

        # Generate SVG barcode
        item.barcode_svg = generate_barcode_svg(item.design_code, item.barcode_type)

        # Save model (triggers pricing calculation internally)
        item.save()
        return item


def update_jewellery_item(item, data, image_file=None):
    """
    Service to explicitly update an existing JewelleryItem.
    Regenerates SKU if cleared, updates barcode SVG on modifications, and saves under a transaction.
    """
    with transaction.atomic():
        old_code = item.design_code
        old_type = item.barcode_type

        for field in [
            "item_name",
            "category",
            "metal_type",
            "weight_in_grams",
            "making_charges",
            "profit_margin",
            "price",
            "stock_quantity",
            "barcode_type",
        ]:
            if field in data:
                setattr(item, field, data[field])

        if data.get("design_code"):
            item.design_code = data["design_code"]
        elif "design_code" in data:  # design_code was explicitly cleared
            item.design_code = generate_next_sku(item.shop.id)

        if image_file:
            item.image = image_file
        elif "image" in data:
            item.image = data["image"]

        # Regenerate barcode graphic if identity details modified
        if item.design_code != old_code or item.barcode_type != old_type or not item.barcode_svg:
            item.barcode_svg = generate_barcode_svg(item.design_code, item.barcode_type)

        item.save()
        return item
