from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.models import Payment, Subscription, SubscriptionEvent


def activate_subscription(
    shop,
    plan,
    is_trial=False,
    amount=0.00,
    payment_ref=None,
    gateway_order_id=None,
    gateway_payment_id=None,
    gateway_signature=None,
):
    """
    Atomic service to activate or renew a subscription/trial for a shop.
    Saves plan snapshots, creates payments, and logs audit events.
    """
    now = timezone.now()
    duration = 7 if is_trial else plan.duration_days
    expires_at = now + timedelta(days=duration)

    # Billing cycle & default features mapping
    billing_cycle = "MONTHLY"
    if plan.duration_days >= 365:
        billing_cycle = "YEARLY"
    elif plan.duration_days >= 90:
        billing_cycle = "QUARTERLY"

    features_snapshot = {
        "barcode": True,
        "repair": True,
        "crm": True,
        "analytics": True if plan.price > 0 else False,
        "api": True if plan.price > 1000 else False,
    }

    with transaction.atomic():
        # 1. Create Subscription
        subscription = Subscription.objects.create(
            shop=shop,
            plan=plan,
            status="TRIAL" if is_trial else "ACTIVE",
            auto_renew=False,
            current_period_start=now,
            current_period_end=expires_at,
            expires_at=expires_at,
            # Snapshots
            plan_name=plan.name,
            plan_price=plan.price if not is_trial else 0.00,
            max_products=plan.max_products,
            max_users=plan.max_users,
            max_invoices_per_month=1000 if not is_trial else 50,
            duration_days=duration,
            billing_cycle=billing_cycle,
            features=features_snapshot,
        )

        # 2. Create Payment record for paid upgrades
        if not is_trial:
            ref = payment_ref or f"PAY-MANUAL-{now.strftime('%Y%m%d%H%M%S')}"
            Payment.objects.create(
                subscription=subscription,
                amount=amount or plan.price,
                currency="INR",
                status="SUCCESS",
                gateway="MANUAL" if not payment_ref else "RAZORPAY",
                payment_reference=ref,
                gateway_order_id=gateway_order_id,
                gateway_payment_id=gateway_payment_id,
                gateway_signature=gateway_signature,
                paid_at=now,
            )

        # 3. Update Shop active pointer & trial tracking
        shop.active_subscription = subscription
        shop.subscription_plan = plan  # Keeping synced temporarily for step 3 migration
        if is_trial:
            shop.trial_used = True
        shop.save()

        # 4. Log SubscriptionEvent
        event_type = "TRIAL_STARTED" if is_trial else "PLAN_UPGRADED"
        # Detect renewal vs upgrade
        if not is_trial and Subscription.objects.filter(shop=shop).exclude(id=subscription.id).exists():
            event_type = "PLAN_RENEWED"

        SubscriptionEvent.objects.create(
            shop=shop,
            subscription=subscription,
            event_type=event_type,
            metadata={
                "plan_id": plan.id,
                "plan_name": plan.name,
                "price": float(amount or plan.price) if not is_trial else 0.00,
                "expires_at": expires_at.isoformat(),
            },
        )

    return subscription
