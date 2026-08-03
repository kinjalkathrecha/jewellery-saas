import factory

from customers.models import Customer

from .shop import ShopFactory


class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Customer

    shop = factory.SubFactory(ShopFactory)
    name = factory.Faker("name")
    mobile_number = factory.Sequence(lambda n: f"+919876543{n:03d}")
