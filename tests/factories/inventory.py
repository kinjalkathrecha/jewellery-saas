from decimal import Decimal

import factory

from inventory.models import Category, JewelleryItem

from .shop import ShopFactory


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    shop = factory.SubFactory(ShopFactory)
    name = factory.Sequence(lambda n: f"Category {n}")


class JewelleryItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = JewelleryItem

    shop = factory.SubFactory(ShopFactory)
    item_name = factory.Sequence(lambda n: f"Jewellery Item {n}")
    category = factory.SubFactory(CategoryFactory, shop=factory.SelfAttribute("..shop"))
    metal_type = "FIXED"
    weight_in_grams = Decimal("5.5")
    price = Decimal("1000.00")
    stock_quantity = 10
    design_code = factory.Sequence(lambda n: f"DES-{n}")
