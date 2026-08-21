import os
import uuid

from django.db import models

from accounts.models import CustomUser
from core.models import Shop
from core.validators import validate_image_upload
from customers.models import Customer


def get_repair_image_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"repair_images/shop_{instance.shop.id}/{uuid.uuid4().hex}{ext}"


class Repair(models.Model):
    STATUS_CHOICES = [
        ("RECEIVED", "Received"),
        ("UNDER_REPAIR", "Under Repair"),
        ("READY", "Ready"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    ]

    PRIORITY_CHOICES = [
        ("NORMAL", "Normal"),
        ("URGENT", "Urgent"),
        ("VIP", "VIP"),
    ]

    ITEM_CATEGORY_CHOICES = [
        ("RING", "Ring"),
        ("CHAIN", "Chain"),
        ("NECKLACE", "Necklace"),
        ("BANGLE", "Bangle"),
        ("EARRING", "Earring"),
        ("OTHER", "Other"),
    ]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="repairs")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="repairs")
    customer_phone_snapshot = models.CharField(max_length=20, blank=True, null=True)
    job_card_number = models.CharField(max_length=50)

    item_category = models.CharField(max_length=50, choices=ITEM_CATEGORY_CHOICES)
    item_weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    item_description = models.TextField(help_text="Describe the item markings, stones, scratches, etc.")
    item_photo = models.ImageField(upload_to=get_repair_image_path, blank=True, null=True, validators=[validate_image_upload])

    repair_type = models.CharField(max_length=100, help_text="e.g. Resizing, Polishing, Stone Setting")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="NORMAL")
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    received_date = models.DateField(auto_now_add=True)
    expected_delivery_date = models.DateField()
    delivered_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name="created_repairs")
    assigned_to = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_repairs"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="RECEIVED")
    internal_notes = models.TextField(blank=True, help_text="Internal shop notes (hidden from customers)")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["shop"]),
            models.Index(fields=["status"]),
            models.Index(fields=["job_card_number"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["shop", "job_card_number"], name="unique_job_card_per_shop"),
            models.CheckConstraint(check=models.Q(estimated_cost__gte=0), name="repair_estimated_cost_positive"),
            models.CheckConstraint(check=models.Q(actual_cost__gte=0), name="repair_actual_cost_positive"),
            models.CheckConstraint(
                check=models.Q(item_weight__gte=0) | models.Q(item_weight__isnull=True),
                name="repair_item_weight_positive",
            ),
        ]

    def __str__(self):
        return f"{self.job_card_number} - {self.customer.name}"


class RepairStatusHistory(models.Model):
    repair = models.ForeignKey(Repair, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20, null=True, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.repair.job_card_number}: {self.from_status} -> {self.to_status} at {self.changed_at}"
