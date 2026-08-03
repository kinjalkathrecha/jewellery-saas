import pytest

from core.models import Payment, SubscriptionEvent
from core.services.subscription import activate_subscription
from tests.factories import ShopFactory, SubscriptionPlanFactory


@pytest.mark.django_db
def test_activate_subscription_trial():
    shop = ShopFactory()
    plan = SubscriptionPlanFactory(duration_days=30)

    subscription = activate_subscription(shop, plan, is_trial=True)

    assert subscription.status == "TRIAL"
    assert subscription.duration_days == 7
    assert shop.active_subscription == subscription
    assert shop.trial_used is True

    assert Payment.objects.filter(subscription=subscription).count() == 0

    event = SubscriptionEvent.objects.filter(shop=shop, subscription=subscription).first()
    assert event is not None
    assert event.event_type == "TRIAL_STARTED"


@pytest.mark.django_db
def test_activate_subscription_paid():
    shop = ShopFactory()
    plan = SubscriptionPlanFactory(duration_days=30, price=499.00)

    subscription = activate_subscription(shop, plan, is_trial=False, amount=499.00, payment_ref="PAY-123")

    assert subscription.status == "ACTIVE"
    assert subscription.duration_days == 30
    assert shop.active_subscription == subscription

    payment = Payment.objects.filter(subscription=subscription).first()
    assert payment is not None
    assert payment.amount == 499.00
    assert payment.payment_reference == "PAY-123"

    event = SubscriptionEvent.objects.filter(shop=shop, subscription=subscription).first()
    assert event is not None
    assert event.event_type == "PLAN_UPGRADED"
