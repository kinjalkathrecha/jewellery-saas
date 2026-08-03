from datetime import timedelta

import factory
from django.utils import timezone

from core.models import Subscription, SubscriptionPlan

from .shop import ShopFactory


class SubscriptionPlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SubscriptionPlan

    name = factory.Sequence(lambda n: f"Plan {n}")
    price = 100.00
    duration_days = 30
    max_products = 1000
    max_users = 3


class SubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subscription

    shop = factory.SubFactory(ShopFactory)
    plan = factory.SubFactory(SubscriptionPlanFactory)
    status = "ACTIVE"
    auto_renew = False

    current_period_start = factory.LazyFunction(timezone.now)
    current_period_end = factory.LazyAttribute(lambda o: o.current_period_start + timedelta(days=o.duration_days))
    expires_at = factory.LazyAttribute(lambda o: o.current_period_end)

    plan_name = factory.SelfAttribute("plan.name")
    plan_price = factory.SelfAttribute("plan.price")
    max_products = factory.SelfAttribute("plan.max_products")
    max_users = factory.SelfAttribute("plan.max_users")
    duration_days = factory.SelfAttribute("plan.duration_days")
