import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jewellery_saas.settings")
django.setup()
from accounts.models import CustomUser
from core.models import Shop, SubscriptionPlan


def setup_qa():
    print("Setting up QA Environment...")
    
    # Create Plan
    plan, _ = SubscriptionPlan.objects.get_or_create(
        name="Standard Plan",
        defaults={'price': 1499.00, 'duration_days': 30, 'max_products': 1000, 'max_users': 5}
    )
    # Shop A
    shop_a, created_a = Shop.objects.get_or_create(
        email="info@shivjewellery.com",
        defaults={
            'name': "Shiv Jewellery",
            'owner_name': "Shiv Owner",
            'phone_number': "9998887770",
            'subscription_plan': plan,
        }
    )
    if created_a or not shop_a.active_subscription:
        from core.services.subscription import activate_subscription
        activate_subscription(shop_a, plan, is_trial=False)
    
    if not CustomUser.objects.filter(username="admin1").exists():
        CustomUser.objects.create_user(
            username="admin1",
            email="admin1@shiv.com",
            password="adminpassword1",
            shop=shop_a,
            role="ADMIN"
        )
        print("Admin user 'admin1' created (password: adminpassword1)")
        
    if not CustomUser.objects.filter(username="staff1").exists():
        CustomUser.objects.create_user(
            username="staff1",
            email="staff1@shiv.com",
            password="staffpassword1",
            shop=shop_a,
            role="STAFF"
        )
        print("Staff user 'staff1' created (password: staffpassword1)")
    # Shop B
    shop_b, created_b = Shop.objects.get_or_create(
        email="info@moonlightjewels.com",
        defaults={
            'name': "Moonlight Jewels",
            'owner_name': "Moonlight Owner",
            'phone_number': "9998887771",
            'subscription_plan': plan,
        }
    )
    if created_b or not shop_b.active_subscription:
        from core.services.subscription import activate_subscription
        activate_subscription(shop_b, plan, is_trial=False)
    
    if not CustomUser.objects.filter(username="admin2").exists():
        CustomUser.objects.create_user(
            username="admin2",
            email="admin2@moonlight.com",
            password="adminpassword2",
            shop=shop_b,
            role="ADMIN"
        )
        print("Admin user 'admin2' created (password: adminpassword2)")
        
    if not CustomUser.objects.filter(username="staff2").exists():
        CustomUser.objects.create_user(
            username="staff2",
            email="staff2@moonlight.com",
            password="staffpassword2",
            shop=shop_b,
            role="STAFF"
        )
        print("Staff user 'staff2' created (password: staffpassword2)")
        
    print("QA Environment setup completed successfully.")
if __name__ == "__main__":
    setup_qa()
