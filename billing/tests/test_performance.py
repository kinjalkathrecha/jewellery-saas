import pytest
from django.test import Client
from django.urls import reverse

from tests.factories import (
    InvoiceFactory,
    InvoiceItemFactory,
    ShopFactory,
    SubscriptionFactory,
    SubscriptionPlanFactory,
)


@pytest.mark.django_db
def test_invoice_detail_query_budget(django_assert_num_queries):
    shop = ShopFactory()
    plan = SubscriptionPlanFactory()
    sub = SubscriptionFactory(shop=shop, plan=plan)
    shop.active_subscription = sub
    shop.save()

    from django.contrib.auth import get_user_model

    User = get_user_model()
    User.objects.create_user(username="admin1", email="admin1@test.com", password="password", shop=shop, role="ADMIN")

    invoice = InvoiceFactory(shop=shop)
    InvoiceItemFactory.create_batch(5, invoice=invoice)

    client = Client()
    client.login(username="admin1", password="password")
    url = reverse("billing:invoice_detail", kwargs={"pk": invoice.pk})

    with django_assert_num_queries(9):
        response = client.get(url)
        assert response.status_code == 200
