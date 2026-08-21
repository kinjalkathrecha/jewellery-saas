from datetime import timedelta
import os
import uuid

from django.db import models
from django.utils import timezone
from core.validators import validate_image_upload

def get_shop_logo_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"shop_logos/{uuid.uuid4().hex}{ext}"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(default=30)
    max_products = models.IntegerField(default=1000)
    max_users = models.IntegerField(default=3)

    def __str__(self):
        return self.name


class Shop(models.Model):
    name = models.CharField(max_length=255)
    owner_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField(blank=True, null=True)
    gstin = models.CharField(max_length=50, blank=True, null=True, verbose_name="GSTIN / Tax Details")
    logo = models.ImageField(upload_to=get_shop_logo_path, blank=True, null=True, validators=[validate_image_upload])
    terms_and_conditions = models.TextField(
        blank=True, null=True, help_text="These will appear at the bottom of your invoices"
    )

    subscription_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True)
    active_subscription = models.ForeignKey(
        "Subscription", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    trial_used = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Barcode & SKU Configuration
    next_sku_number = models.IntegerField(default=1)
    sku_prefix = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Custom SKU prefix (e.g. SHIV). If empty, defaults to shop name initials.",
    )
    scanner_suffix = models.CharField(
        max_length=10, choices=[("ENTER", "Enter"), ("TAB", "Tab"), ("NONE", "No Suffix")], default="ENTER"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = not self.pk
        if is_new and not self.trial_ends_at:
            # 7 days trial by default
            self.trial_ends_at = timezone.now() + timedelta(days=7)
        
        # Smart invalidation check
        should_invalidate_sub = True
        if not is_new:
            try:
                original = self.__class__.objects.get(pk=self.pk)
                if original.active_subscription_id == self.active_subscription_id and original.trial_ends_at == self.trial_ends_at:
                    should_invalidate_sub = False
            except self.__class__.DoesNotExist:
                pass

        super().save(*args, **kwargs)
        from core.services import cache_service

        if should_invalidate_sub:
            cache_service.invalidate_subscription(self.id)
        cache_service.invalidate_dashboard(self.id)

    def delete(self, *args, **kwargs):
        shop_id = self.id
        super().delete(*args, **kwargs)
        from core.services import cache_service

        cache_service.invalidate_subscription(shop_id)
        cache_service.invalidate_dashboard(shop_id)

    def _calculate_subscription_status(self):
        from django.conf import settings
        grace_days = getattr(settings, "SUBSCRIPTION_GRACE_DAYS", 3)
        now = timezone.now()

        if not self.is_active:
            return {
                "active": False,
                "status": "DISABLED",
                "message": "Shop deactivated by administrator.",
                "days_left": 0,
                "is_locked": True,
            }

        sub = self.active_subscription
        if not sub:
            return {
                "active": False,
                "status": "NO_PLAN",
                "message": "No active subscription plan.",
                "days_left": 0,
                "is_locked": True,
            }

        expires_at = sub.expires_at
        grace_ends_at = expires_at + timedelta(days=grace_days)
        is_trial = sub.status == "TRIAL"

        if now < expires_at:
            delta = expires_at - now
            days_left = max(0, delta.days)
            if days_left > 0:
                msg = (
                    f"Trial active. {days_left} days remaining." if is_trial else f"Active. {days_left} days remaining."
                )
            else:
                hours_left = max(0, int(delta.total_seconds() / 3600))
                msg = (
                    f"Trial expires in {hours_left} hours."
                    if is_trial
                    else f"Subscription expires in {hours_left} hours."
                )
            return {
                "active": True,
                "status": sub.status,
                "message": msg,
                "days_left": days_left,
                "is_locked": False,
            }
        elif now < grace_ends_at:
            delta = grace_ends_at - now
            days_left = max(0, delta.days)
            if days_left > 0:
                msg = f"Subscription expired. Grace period ends in {days_left} days."
            else:
                hours_left = max(0, int(delta.total_seconds() / 3600))
                msg = f"Subscription expired. Grace period ends in {hours_left} hours."
            return {
                "active": True,
                "status": "GRACE_PERIOD",
                "message": msg,
                "days_left": days_left,
                "is_locked": False,
            }
        else:
            delta = now - expires_at
            days_ago = delta.days
            return {
                "active": False,
                "status": "EXPIRED",
                "message": f"Subscription expired {days_ago} days ago. Upgrade required.",
                "days_left": 0,
                "is_locked": True,
            }

    def get_subscription_status(self):
        from core.services import cache_service
        return cache_service.get_or_set_subscription_status(self.id, self._calculate_subscription_status)

    def __str__(self):
        return self.name


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACTIVE", "Active"),
        ("FAILED", "Failed"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
        ("REFUNDED", "Refunded"),
        ("TRIAL", "Trial"),
    ]
    BILLING_CYCLES = [
        ("MONTHLY", "Monthly"),
        ("QUARTERLY", "Quarterly"),
        ("YEARLY", "Yearly"),
        ("LIFETIME", "Lifetime"),
    ]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE", db_index=True)
    auto_renew = models.BooleanField(default=False)
    renewal_notified_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Snapshot Fields
    plan_name = models.CharField(max_length=100)
    plan_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_products = models.IntegerField()
    max_users = models.IntegerField()
    max_invoices_per_month = models.IntegerField(default=1000)
    duration_days = models.IntegerField()
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLES, default="MONTHLY")
    features = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.plan_name} for {self.shop.name} ({self.status})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from core.services import cache_service

        cache_service.invalidate_subscription(self.shop.id)

    def delete(self, *args, **kwargs):
        shop_id = self.shop.id
        super().delete(*args, **kwargs)
        from core.services import cache_service

        cache_service.invalidate_subscription(shop_id)


class Payment(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SUCCESS", db_index=True)
    gateway = models.CharField(max_length=50, default="MANUAL")
    payment_reference = models.CharField(max_length=100)
    gateway_order_id = models.CharField(max_length=100, null=True, blank=True)
    gateway_payment_id = models.CharField(max_length=100, null=True, blank=True)
    gateway_signature = models.CharField(max_length=255, null=True, blank=True)
    invoice_number = models.CharField(max_length=100, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Payment {self.payment_reference} - {self.amount} {self.currency}"


class SubscriptionEvent(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="subscription_events")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=50)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.event_type} - {self.shop.name} at {self.created_at}"


class Lead(models.Model):
    LEAD_TYPES = [
        ("DEMO", "Demo Request"),
        ("CONTACT", "General Contact"),
        ("NEWSLETTER", "Newsletter Signup"),
    ]
    STATUS_CHOICES = [
        ("NEW", "New"),
        ("CONTACTED", "Contacted"),
        ("DEMO", "Demo Scheduled"),
        ("CONVERTED", "Converted"),
        ("LOST", "Lost"),
    ]
    name = models.CharField(max_length=255)
    shop_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField(blank=True)
    lead_type = models.CharField(max_length=20, choices=LEAD_TYPES, default="CONTACT")
    source = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="NEW")
    notes = models.TextField(blank=True)
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.shop_name or self.email} ({self.get_lead_type_display()})"
