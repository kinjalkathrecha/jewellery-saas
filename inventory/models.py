import uuid
import os

from django.db import models
from django.utils import timezone

from core.models import Shop
from core.validators import validate_image_upload

def get_jewellery_image_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"jewellery_images/{instance.uuid.hex}{ext}"


class Category(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.shop.name})"


class MetalRate(models.Model):
    METAL_CHOICES = [
        ("GOLD_24K", "Gold 24K"),
        ("GOLD_22K", "Gold 22K"),
        ("GOLD_18K", "Gold 18K"),
        ("SILVER", "Silver"),
    ]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="metal_rates")
    metal_type = models.CharField(max_length=20, choices=METAL_CHOICES)
    rate_per_gram = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateTimeField(default=timezone.now)
    source = models.CharField(max_length=50, default="MANUAL")
    created_by = models.ForeignKey("accounts.CustomUser", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_from", "-created_at"]

    @classmethod
    def get_current_rate(cls, shop, metal_type):
        from core.services import cache_service

        cached_rate = cache_service.get_metal_rate(shop.id, metal_type)
        if cached_rate is not None:
            return cached_rate
        rate_obj = (
            cls.objects.filter(shop=shop, metal_type=metal_type).order_by("-effective_from", "-created_at").first()
        )
        rate = rate_obj.rate_per_gram if rate_obj else None
        if rate is not None:
            cache_service.set_metal_rate(shop.id, metal_type, rate)
        return rate

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from core.services import cache_service

        cache_service.invalidate_rates(self.shop.id, self.metal_type)

    def delete(self, *args, **kwargs):
        shop_id = self.shop.id
        metal_type = self.metal_type
        super().delete(*args, **kwargs)
        from core.services import cache_service

        cache_service.invalidate_rates(shop_id, metal_type)

    def __str__(self):
        return f"{self.get_metal_type_display()}: {self.rate_per_gram}/g at {self.effective_from}"


class JewelleryItem(models.Model):
    METAL_CHOICES = [
        ("GOLD_24K", "Gold 24K"),
        ("GOLD_22K", "Gold 22K"),
        ("GOLD_18K", "Gold 18K"),
        ("SILVER", "Silver"),
        ("FIXED", "Fixed Price (Manual)"),
    ]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="items")
    item_name = models.CharField(max_length=200, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    metal_type = models.CharField(max_length=20, choices=METAL_CHOICES, default="FIXED")
    weight_in_grams = models.DecimalField(max_digits=10, decimal_places=3)
    making_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    metal_rate_used = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    metal_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    profit_margin = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price = models.DecimalField(max_digits=15, decimal_places=2)  # represents selling price
    stock_quantity = models.IntegerField(default=0)
    design_code = models.CharField(max_length=50, blank=True, null=True)
    image = models.ImageField(upload_to=get_jewellery_image_path, blank=True, null=True, validators=[validate_image_upload])

    # Barcode & UUID additions
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    barcode_type = models.CharField(
        max_length=20, choices=[("CODE128", "Code 128"), ("EAN13", "EAN 13"), ("QR", "QR Code")], default="CODE128"
    )
    barcode_svg = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["shop", "design_code"], name="unique_shop_design_code")]
        indexes = [
            models.Index(fields=["shop", "design_code"]),
            models.Index(fields=["uuid"]),
            models.Index(fields=["shop", "created_at"]),
            models.Index(fields=["metal_type", "price"]),
        ]

    def calculate_price_for_rate(self, rate_per_gram):
        if self.metal_type == "FIXED":
            return self.price
        metal_cost = self.weight_in_grams * rate_per_gram
        return metal_cost + self.making_charges + self.profit_margin

    def get_current_price(self):
        if self.metal_type == "FIXED":
            return self.price
        rate = MetalRate.get_current_rate(self.shop, self.metal_type)
        if rate is not None:
            return (self.weight_in_grams * rate) + self.making_charges + self.profit_margin
        return self.price

    def save(self, *args, **kwargs):
        from decimal import Decimal
        self.weight_in_grams = Decimal(str(self.weight_in_grams))
        self.making_charges = Decimal(str(self.making_charges))
        self.profit_margin = Decimal(str(self.profit_margin))
        self.metal_rate_used = Decimal(str(self.metal_rate_used))
        self.price = Decimal(str(self.price))

        if self.metal_type and self.metal_type != "FIXED":
            rate = MetalRate.get_current_rate(self.shop, self.metal_type)
            if rate is not None:
                self.metal_rate_used = Decimal(str(rate))
            self.metal_cost = self.weight_in_grams * self.metal_rate_used
            self.price = self.metal_cost + self.making_charges + self.profit_margin
        else:
            self.metal_rate_used = Decimal("0.00")
            self.metal_cost = Decimal("0.00")
            self.profit_margin = Decimal("0.00")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} - {self.design_code}"
