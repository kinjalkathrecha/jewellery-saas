from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from inventory.models import MetalRate
from tests.factories import JewelleryItemFactory, ShopFactory


@pytest.mark.django_db
def test_jewellery_item_fixed_pricing():
    item = JewelleryItemFactory(metal_type='FIXED', price=Decimal("500.00"))
    assert item.get_current_price() == 500.00

@pytest.mark.django_db
def test_jewellery_item_dynamic_pricing():
    shop = ShopFactory()
    User = get_user_model()
    user = User.objects.create_user(username="testu", email="t@example.com", password="pwd", shop=shop)
    
    MetalRate.objects.create(
        shop=shop,
        metal_type='GOLD_24K',
        rate_per_gram=Decimal("5000.00"),
        created_by=user
    )
    
    item = JewelleryItemFactory(
        shop=shop,
        metal_type='GOLD_24K',
        weight_in_grams=Decimal("2.00"),
        making_charges=Decimal("500.00"),
        profit_margin=Decimal("300.00")
    )
    
    assert item.get_current_price() == 10800.00
