import factory

from billing.models import Invoice, InvoiceItem

from .customers import CustomerFactory
from .inventory import JewelleryItemFactory
from .shop import ShopFactory


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    shop = factory.SubFactory(ShopFactory)
    customer = factory.SubFactory(CustomerFactory, shop=factory.SelfAttribute('..shop'))
    invoice_number = factory.Sequence(lambda n: f"INV-{n:05d}")
    subtotal = 1000.00
    tax_amount = 30.00
    total_amount = 1030.00

class InvoiceItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InvoiceItem

    invoice = factory.SubFactory(InvoiceFactory)
    item = factory.SubFactory(JewelleryItemFactory, shop=factory.SelfAttribute('..invoice.shop'))
    quantity = 1
    rate = 1000.00
    amount = 1000.00
