from datetime import timedelta

import pytest
from django.utils import timezone

from tests.factories import ShopFactory, SubscriptionFactory


@pytest.mark.django_db
def test_shop_subscription_status_no_plan():
    shop = ShopFactory(active_subscription=None)
    status = shop.get_subscription_status()
    assert status['status'] == 'NO_PLAN'
    assert status['is_locked'] is True
    assert status['active'] is False

@pytest.mark.django_db
def test_shop_subscription_status_active():
    shop = ShopFactory()
    subscription = SubscriptionFactory(shop=shop, status='ACTIVE', expires_at=timezone.now() + timedelta(days=10))
    shop.active_subscription = subscription
    shop.save()
    
    status = shop.get_subscription_status()
    assert status['status'] == 'ACTIVE'
    assert status['is_locked'] is False
    assert status['active'] is True

@pytest.mark.django_db
def test_shop_subscription_status_grace_period():
    shop = ShopFactory()
    subscription = SubscriptionFactory(shop=shop, status='ACTIVE', expires_at=timezone.now() - timedelta(days=1))
    shop.active_subscription = subscription
    shop.save()
    
    status = shop.get_subscription_status()
    assert status['status'] == 'GRACE_PERIOD'
    assert status['is_locked'] is False
    assert status['active'] is True

@pytest.mark.django_db
def test_shop_subscription_status_expired():
    shop = ShopFactory()
    subscription = SubscriptionFactory(shop=shop, status='ACTIVE', expires_at=timezone.now() - timedelta(days=4))
    shop.active_subscription = subscription
    shop.save()
    
    status = shop.get_subscription_status()
    assert status['status'] == 'EXPIRED'
    assert status['is_locked'] is True
    assert status['active'] is False

@pytest.mark.django_db
def test_shop_deactivated():
    shop = ShopFactory(is_active=False)
    status = shop.get_subscription_status()
    assert status['status'] == 'DISABLED'
    assert status['is_locked'] is True
    assert status['active'] is False
