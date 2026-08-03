from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from core.models import Shop, SubscriptionPlan
from inventory.models import Category, MetalRate


class ShopSignupTests(TestCase):
    def setUp(self):
        # 1. Create a subscription plan to choose from during registration
        self.plan = SubscriptionPlan.objects.create(
            name="Starter Plan",
            price=499.00,
            duration_days=30,
            max_products=200,
            max_users=2
        )
        self.signup_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')

    def test_signup_page_loads(self):
        """Verify the shop signup page loads successfully and displays the plan."""
        response = self.client.get(self.signup_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Register Your Jewellery Shop")
        self.assertContains(response, "Starter Plan")

    def test_successful_shop_registration(self):
        """Verify that a valid POST request successfully registers a shop, admin user, and seeds data."""
        payload = {
            'shop_name': "Sparkle Jewellers",
            'owner_name': "Jane Sparkle",
            'shop_email': "contact@sparkle.com",
            'shop_phone': "9998887776",
            'subscription_plan': self.plan.id,
            'username': "janesparkle",
            'admin_email': "jane@sparkle.com",
            'password': "securepassword123",
            'password_confirm': "securepassword123",
        }
        
        response = self.client.post(self.signup_url, data=payload)
        
        # Verify redirect to login page
        self.assertRedirects(response, self.login_url)

        # Verify Shop creation
        shop = Shop.objects.filter(email="contact@sparkle.com").first()
        self.assertIsNotNone(shop)
        self.assertEqual(shop.name, "Sparkle Jewellers")
        self.assertEqual(shop.subscription_plan, self.plan)

        # Verify Admin User creation
        user = CustomUser.objects.filter(username="janesparkle").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.shop, shop)
        self.assertEqual(user.role, 'ADMIN')
        self.assertTrue(user.check_password("securepassword123"))

        # Verify Category seeding
        categories = Category.objects.filter(shop=shop)
        self.assertEqual(categories.count(), 2)
        self.assertTrue(categories.filter(name="Gold Rings").exists())
        self.assertTrue(categories.filter(name="Diamond Necklaces").exists())

        # Verify MetalRate seeding
        rates = MetalRate.objects.filter(shop=shop)
        self.assertEqual(rates.count(), 4)
        self.assertTrue(rates.filter(metal_type="GOLD_24K", rate_per_gram=7000.00).exists())
        self.assertTrue(rates.filter(metal_type="SILVER", rate_per_gram=90.00).exists())

    def test_signup_validation_mismatched_passwords(self):
        """Verify password confirm mismatch results in form error."""
        payload = {
            'shop_name': "Sparkle Jewellers",
            'owner_name': "Jane Sparkle",
            'shop_email': "contact@sparkle.com",
            'shop_phone': "9998887776",
            'subscription_plan': self.plan.id,
            'username': "janesparkle",
            'admin_email': "jane@sparkle.com",
            'password': "securepassword123",
            'password_confirm': "differentpassword",
        }
        
        response = self.client.post(self.signup_url, data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'password_confirm', "Passwords do not match.")

    def test_signup_validation_duplicate_shop_email(self):
        """Verify registering a shop with an email that already exists fails."""
        # Create an existing shop
        Shop.objects.create(
            name="Existing Shop",
            owner_name="Owner",
            email="contact@sparkle.com",
            phone_number="123",
            subscription_plan=self.plan
        )
        
        payload = {
            'shop_name': "Sparkle Jewellers",
            'owner_name': "Jane Sparkle",
            'shop_email': "contact@sparkle.com", # Duplicate
            'shop_phone': "9998887776",
            'subscription_plan': self.plan.id,
            'username': "janesparkle",
            'admin_email': "jane@sparkle.com",
            'password': "securepassword123",
            'password_confirm': "securepassword123",
        }
        
        response = self.client.post(self.signup_url, data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'shop_email', "A shop with this email address is already registered.")

    def test_signup_validation_duplicate_username(self):
        """Verify registering with a username that already exists fails."""
        # Create an existing user
        CustomUser.objects.create_user(
            username="janesparkle",
            email="other@email.com",
            password="pwd"
        )
        
        payload = {
            'shop_name': "Sparkle Jewellers",
            'owner_name': "Jane Sparkle",
            'shop_email': "contact@sparkle.com",
            'shop_phone': "9998887776",
            'subscription_plan': self.plan.id,
            'username': "janesparkle", # Duplicate
            'admin_email': "jane@sparkle.com",
            'password': "securepassword123",
            'password_confirm': "securepassword123",
        }
        
        response = self.client.post(self.signup_url, data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'username', "This username is already taken.")

