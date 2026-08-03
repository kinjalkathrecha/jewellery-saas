from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import CustomUser
from core.models import Shop, SubscriptionPlan
from core.services.subscription import activate_subscription


class DashboardReportsTestCase(TestCase):
    def setUp(self):
        # 1. Setup subscription plan
        self.plan = SubscriptionPlan.objects.create(
            name="Test Plan", price=100.0, duration_days=30, max_products=100, max_users=3
        )
        
        # 2. Setup Shop
        self.shop = Shop.objects.create(
            name="Test Shop", email="test@reports.com", phone_number="12345"
        )
        
        # Activate subscription
        activate_subscription(self.shop, self.plan, is_trial=False)
        
        # 3. Create User
        self.user = CustomUser.objects.create_user(
            username="reportsadmin",
            email="reports@test.com",
            password="testpassword",
            shop=self.shop,
            role="ADMIN"
        )
        
        # Client
        self.client = Client()
        self.client.login(username="reportsadmin", password="testpassword")

    def test_reports_view_accessible(self):
        url = reverse('dashboard:business_reports')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/reports.html')
        self.assertIn('total_sales_count', response.context)
        self.assertIn('sales_trend', response.context)
        self.assertIn('metal_labels', response.context)

    def test_home_view_accessible(self):
        url = reverse('dashboard:home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/home.html')

