import pytest
from django.test import Client
from django.urls import reverse

from tests.factories import (
    CustomerFactory,
    JewelleryItemFactory,
    ShopFactory,
    SubscriptionFactory,
    SubscriptionPlanFactory,
)


@pytest.mark.django_db
def test_invoice_creation_business_logic():
    shop = ShopFactory()
    plan = SubscriptionPlanFactory()
    sub = SubscriptionFactory(shop=shop, plan=plan)
    shop.active_subscription = sub
    shop.save()
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    User.objects.create_user(
        username="admin1", email="admin1@test.com", password="password", shop=shop, role="ADMIN"
    )
    
    customer = CustomerFactory(shop=shop, total_spent=100.00)
    item = JewelleryItemFactory(shop=shop, stock_quantity=10, price=1000.00)
    
    client = Client()
    client.login(username="admin1", password="password")
    
    form_data = {
        'customer': customer.id,
        'invoice_number': 'INV-TEST-001',
        'tax_amount': 30.00,
        'items-TOTAL_FORMS': '1',
        'items-INITIAL_FORMS': '0',
        'items-MIN_NUM_FORMS': '0',
        'items-MAX_NUM_FORMS': '1000',
        
        'items-0-item': item.id,
        'items-0-quantity': '2',
        'items-0-rate': '1000.00',
        'items-0-amount': '2000.00'
    }
    
    url = reverse('billing:invoice_add')
    response = client.post(url, form_data)
    assert response.status_code == 302
    
    item.refresh_from_db()
    assert item.stock_quantity == 8
    
    customer.refresh_from_db()
    assert float(customer.total_spent) == 2130.00
