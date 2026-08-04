import pytest
from django.core.cache import cache
from django.utils import timezone
from tests.factories.shop import ShopFactory
from tests.factories.subscriptions import SubscriptionPlanFactory, SubscriptionFactory
from inventory.models import MetalRate
from core.services import cache_service

@pytest.mark.django_db
class TestCachingService:
    def setup_method(self):
        cache.clear()
        self.shop = ShopFactory(name="Test Cache Shop")
        self.plan = SubscriptionPlanFactory()

    def test_metal_rate_caching(self):
        # Create a metal rate
        rate1 = MetalRate.objects.create(
            shop=self.shop,
            metal_type="GOLD_24K",
            rate_per_gram=100.00,
            effective_from=timezone.now()
        )

        # First lookup: fetches from DB and caches it
        r1 = MetalRate.get_current_rate(self.shop, "GOLD_24K")
        assert float(r1) == 100.00

        # Set cache to custom value directly to test cache hit
        cache_service.set_metal_rate(self.shop.id, "GOLD_24K", 150.00)

        # Second lookup should hit cache
        r2 = MetalRate.get_current_rate(self.shop, "GOLD_24K")
        assert float(r2) == 150.00

        # Modify rate1 (save() triggers invalidation)
        rate1.rate_per_gram = 200.00
        rate1.save()

        # Lookup should now hit DB again
        r3 = MetalRate.get_current_rate(self.shop, "GOLD_24K")
        assert float(r3) == 200.00

    def test_subscription_status_caching(self):
        sub = SubscriptionFactory(
            shop=self.shop,
            plan=self.plan,
            status="ACTIVE",
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timezone.timedelta(days=30),
            expires_at=timezone.now() + timezone.timedelta(days=30),
            max_products=1000,
            max_users=3,
            duration_days=30
        )
        self.shop.active_subscription = sub
        self.shop.save()

        # First lookup: caches status
        status1 = self.shop.get_subscription_status()
        assert status1["active"] is True

        # Manually alter cache to test cache hit
        custom_status = {"active": False, "status": "EXPIRED", "message": "Expired", "days_left": 0, "is_locked": True}
        cache_service.set_subscription_status(self.shop.id, custom_status)

        status2 = self.shop.get_subscription_status()
        assert status2["active"] is False

        # Invalidate (saving Subscription model triggers invalidation)
        sub.save()

        # Hits database / re-computes again
        status3 = self.shop.get_subscription_status()
        assert status3["active"] is True
