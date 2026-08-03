import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from tests.factories import ShopFactory, SubscriptionFactory, SubscriptionPlanFactory


@pytest.mark.django_db
def test_anonymous_user_blocked_from_dashboard():
    client = Client()
    url = reverse('dashboard:home')
    response = client.get(url)
    assert response.status_code == 302
    assert 'login' in response.url

@pytest.mark.django_db
def test_staff_user_blocked_from_admin_settings():
    shop = ShopFactory()
    plan = SubscriptionPlanFactory()
    subscription = SubscriptionFactory(shop=shop, plan=plan)
    shop.active_subscription = subscription
    shop.save()
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    User.objects.create_user(
        username="staffuser",
        email="staff@example.com",
        password="password123",
        shop=shop,
        role="STAFF"
    )
    
    client = Client()
    client.login(username="staffuser", password="password123")
    
    url = reverse('dashboard:shop_settings')
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == reverse('dashboard:home')

@pytest.mark.django_db
def test_cross_tenant_detail_view_fails():
    shop_a = ShopFactory()
    shop_b = ShopFactory()
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    User.objects.create_user(
        username="usera",
        email="usera@example.com",
        password="password123",
        shop=shop_a,
        role="ADMIN"
    )
    
    from repairs.models import Repair
    from tests.factories import CustomerFactory
    customer_b = CustomerFactory(shop=shop_b)
    
    repair_b = Repair.objects.create(
        shop=shop_b,
        customer=customer_b,
        job_card_number="JC-999",
        item_category="RING",
        item_description="Test Ring",
        repair_type="Resizing",
        expected_delivery_date=timezone.now().date()
    )
    
    client = Client()
    client.login(username="usera", password="password123")
    
    url = reverse('repairs:repair_detail', kwargs={'pk': repair_b.pk})
    response = client.get(url)
    assert response.status_code == 404
