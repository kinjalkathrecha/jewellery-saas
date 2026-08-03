import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from repairs.models import Repair, RepairStatusHistory
from repairs.services import generate_job_card_number, process_repair_status_change
from tests.factories import CustomerFactory, ShopFactory


@pytest.mark.django_db
def test_generate_job_card_number():
    shop = ShopFactory(id=5)
    customer = CustomerFactory(shop=shop)
    repair = Repair(shop=shop, customer=customer)
    job_card = generate_job_card_number(repair)
    assert job_card.startswith("SHOP5-JOB-")

@pytest.mark.django_db
def test_process_repair_status_change_success():
    shop = ShopFactory()
    customer = CustomerFactory(shop=shop)
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(username="staff1", email="staff1@test.com", password="pwd", shop=shop)
    
    repair = Repair.objects.create(
        shop=shop,
        customer=customer,
        job_card_number="JC-200",
        item_category="RING",
        item_description="Test Ring",
        expected_delivery_date=timezone.now().date(),
        status='RECEIVED'
    )
    
    process_repair_status_change(repair, 'UNDER_REPAIR', user, notes="Started resizing")
    repair.refresh_from_db()
    
    assert repair.status == 'UNDER_REPAIR'
    history = RepairStatusHistory.objects.filter(repair=repair).first()
    assert history is not None
    assert history.from_status == 'RECEIVED'
    assert history.to_status == 'UNDER_REPAIR'
    assert history.changed_by == user

@pytest.mark.django_db
def test_process_repair_status_change_invalid():
    shop = ShopFactory()
    customer = CustomerFactory(shop=shop)
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(username="staff2", email="staff2@test.com", password="pwd", shop=shop)
    
    repair = Repair.objects.create(
        shop=shop,
        customer=customer,
        job_card_number="JC-201",
        item_category="RING",
        item_description="Test Ring",
        expected_delivery_date=timezone.now().date(),
        status='RECEIVED'
    )
    
    with pytest.raises(ValidationError):
        process_repair_status_change(repair, 'DELIVERED', user)
