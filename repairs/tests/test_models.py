import pytest
from django.db.utils import IntegrityError
from django.utils import timezone

from repairs.models import Repair, get_repair_image_path
from tests.factories import CustomerFactory, ShopFactory


@pytest.mark.django_db
def test_repair_model_str():
    shop = ShopFactory()
    customer = CustomerFactory(shop=shop, name="John Doe")
    repair = Repair.objects.create(
        shop=shop,
        customer=customer,
        job_card_number="JC-100",
        item_category="RING",
        item_description="Test ring",
        repair_type="Resizing",
        expected_delivery_date=timezone.now().date(),
    )
    assert str(repair) == "JC-100 - John Doe"


@pytest.mark.django_db
def test_repair_image_path_helper():
    shop = ShopFactory()
    customer = CustomerFactory(shop=shop)
    repair = Repair(
        shop=shop,
        customer=customer,
        job_card_number="JC-101",
        item_category="RING",
        item_description="Test ring",
        expected_delivery_date=timezone.now().date(),
    )
    path = get_repair_image_path(repair, "test.png")
    assert path == f"repair_images/shop_{shop.id}/test.png"


@pytest.mark.django_db
def test_repair_estimated_cost_constraint():
    shop = ShopFactory()
    customer = CustomerFactory(shop=shop)
    with pytest.raises(IntegrityError):
        Repair.objects.create(
            shop=shop,
            customer=customer,
            job_card_number="JC-102",
            item_category="RING",
            item_description="Test ring",
            estimated_cost=-10.00,
            expected_delivery_date=timezone.now().date(),
        )
