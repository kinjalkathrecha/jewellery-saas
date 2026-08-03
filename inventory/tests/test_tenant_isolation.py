import pytest
from django.test import Client
from django.urls import reverse

from tests.factories import JewelleryItemFactory, ShopFactory


@pytest.mark.django_db
def test_inventory_tenant_isolation():
    shop_a = ShopFactory()
    shop_b = ShopFactory()

    from django.contrib.auth import get_user_model

    User = get_user_model()
    User.objects.create_user(
        username="usera", email="usera@example.com", password="password123", shop=shop_a, role="ADMIN"
    )

    item_b = JewelleryItemFactory(shop=shop_b, item_name="Shop B Item")

    client = Client()
    client.login(username="usera", password="password123")

    url = reverse("inventory:item_list")
    response = client.get(url)
    assert response.status_code == 200
    assert item_b not in response.context["items"]

    edit_url = reverse("inventory:item_edit", kwargs={"pk": item_b.pk})
    edit_response = client.get(edit_url)
    assert edit_response.status_code == 404
