from django.db import models
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from audit.models import AuditLog
from billing.models import Invoice
from core.middleware import get_current_ip, get_current_user
from core.models import Payment, Shop, Subscription
from inventory.models import JewelleryItem


def get_changes(instance):
    changes = {}
    if not instance.pk:
        return changes
    try:
        old_instance = instance.__class__.objects.get(pk=instance.pk)
        for field in instance._meta.fields:
            field_name = field.name

            # Avoid comparing binary or text representation of files/images since they don't serialize easily
            if isinstance(field, (models.FileField, models.ImageField)):
                continue

            old_val = getattr(old_instance, field_name)
            new_val = getattr(instance, field_name)
            if old_val != new_val:
                changes[field_name] = [str(old_val), str(new_val)]
    except Exception:
        pass
    return changes


_deleting_shops = set()


@receiver(pre_delete, sender=Shop)
def track_shop_deletion(sender, instance, **kwargs):
    _deleting_shops.add(instance.pk)


@receiver(post_delete, sender=Shop)
def untrack_shop_deletion(sender, instance, **kwargs):
    _deleting_shops.discard(instance.pk)


def get_safe_shop(instance):
    shop = getattr(instance, "shop", None)
    if shop and shop.pk:
        if shop.pk in _deleting_shops:
            return None
        if not Shop.objects.filter(pk=shop.pk).exists():
            return None
    return shop


@receiver(pre_save, sender=Subscription)
@receiver(pre_save, sender=JewelleryItem)
@receiver(pre_save, sender=Invoice)
@receiver(pre_save, sender=Payment)
def audit_pre_save(sender, instance, **kwargs):
    # Store changes on the instance temporarily
    instance._audit_changes = get_changes(instance)


@receiver(post_save, sender=Subscription)
@receiver(post_save, sender=JewelleryItem)
@receiver(post_save, sender=Invoice)
@receiver(post_save, sender=Payment)
def audit_post_save(sender, instance, created, **kwargs):
    user = get_current_user()
    ip_address = get_current_ip()

    # Resolve shop safely
    shop = get_safe_shop(instance)

    action = "CREATE" if created else "UPDATE"
    changes = getattr(instance, "_audit_changes", {})

    if not created and not changes:
        return  # No changes made

    if created:
        for f in instance._meta.fields:
            # Skip file fields from initial payload
            if isinstance(f, (models.FileField, models.ImageField)):
                continue
            changes[f.name] = ["", str(getattr(instance, f.name))]

    AuditLog.objects.create(
        shop=shop,
        user=user if user and user.is_authenticated else None,
        action=action,
        model_name=sender.__name__,
        object_id=instance.pk,
        changes=changes,
        ip_address=ip_address,
    )


@receiver(post_delete, sender=Subscription)
@receiver(post_delete, sender=JewelleryItem)
@receiver(post_delete, sender=Invoice)
@receiver(post_delete, sender=Payment)
def audit_post_delete(sender, instance, **kwargs):
    user = get_current_user()
    ip_address = get_current_ip()

    # Resolve shop safely
    shop = get_safe_shop(instance)

    changes = {}
    for f in instance._meta.fields:
        if isinstance(f, (models.FileField, models.ImageField)):
            continue
        changes[f.name] = [str(getattr(instance, f.name)), ""]

    AuditLog.objects.create(
        shop=shop,
        user=user if user and user.is_authenticated else None,
        action="DELETE",
        model_name=sender.__name__,
        object_id=instance.pk,
        changes=changes,
        ip_address=ip_address,
    )
