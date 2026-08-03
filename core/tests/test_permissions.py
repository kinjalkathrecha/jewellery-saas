import pytest

from core.services.permissions import PlanPermissionService
from tests.factories import (
    JewelleryItemFactory,
    ShopFactory,
    SubscriptionFactory,
    SubscriptionPlanFactory,
)


@pytest.mark.django_db
def test_permission_service_product_limit():
    shop = ShopFactory()
    plan = SubscriptionPlanFactory(max_products=2)
    subscription = SubscriptionFactory(shop=shop, plan=plan)
    shop.active_subscription = subscription
    shop.save()

    assert PlanPermissionService.check(shop, "create_product") is True

    JewelleryItemFactory.create_batch(2, shop=shop)

    assert PlanPermissionService.check(shop, "create_product") is False


@pytest.mark.django_db
def test_permission_service_locked_status():
    shop = ShopFactory()
    from datetime import timedelta

    from django.utils import timezone

    subscription = SubscriptionFactory(shop=shop, status="EXPIRED", expires_at=timezone.now() - timedelta(days=5))
    shop.active_subscription = subscription
    shop.save()

    assert PlanPermissionService.check(shop, "create_product") is False
    assert PlanPermissionService.check(shop, "create_repair") is False
