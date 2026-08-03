import factory

from core.models import Shop


class ShopFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Shop

    name = factory.Sequence(lambda n: f"Shop {n}")
    owner_name = factory.Faker("name")
    email = factory.Sequence(lambda n: f"shop_{n}@example.com")
    phone_number = factory.Sequence(lambda n: f"+919876543{n:03d}")
    address = factory.Faker("address")
