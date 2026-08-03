from django.core.management.base import BaseCommand

from accounts.models import CustomUser
from core.models import Shop, SubscriptionPlan
from core.services.subscription import activate_subscription


class Command(BaseCommand):
    help = "Seeds database with initial plans, shops, and user accounts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--qa",
            action="store_true",
            help="Seeds typical standard QA shops and users",
        )
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Seeds demo shops and users",
        )

    def handle(self, *args, **options):
        # We default to QA if no arguments are passed
        is_qa = options["qa"] or not options["demo"]

        self.stdout.write("Setting up Seeding Environment...")

        # Create standard plans
        plan, _ = SubscriptionPlan.objects.get_or_create(
            name="Standard Plan", defaults={"price": 1499.00, "duration_days": 30, "max_products": 1000, "max_users": 5}
        )

        if is_qa:
            self.stdout.write("Seeding QA data...")
            # Shop A
            shop_a, created_a = Shop.objects.get_or_create(
                email="info@shivjewellery.com",
                defaults={
                    "name": "Shiv Jewellery",
                    "owner_name": "Shiv Owner",
                    "phone_number": "9998887770",
                    "subscription_plan": plan,
                },
            )
            if created_a or not shop_a.active_subscription:
                activate_subscription(shop_a, plan, is_trial=False)

            if not CustomUser.objects.filter(username="admin1").exists():
                CustomUser.objects.create_user(
                    username="admin1", email="admin1@shiv.com", password="adminpassword1", shop=shop_a, role="ADMIN"
                )
                self.stdout.write(self.style.SUCCESS("Admin user 'admin1' created (password: adminpassword1)"))

            if not CustomUser.objects.filter(username="staff1").exists():
                CustomUser.objects.create_user(
                    username="staff1", email="staff1@shiv.com", password="staffpassword1", shop=shop_a, role="STAFF"
                )
                self.stdout.write(self.style.SUCCESS("Staff user 'staff1' created (password: staffpassword1)"))

            # Shop B
            shop_b, created_b = Shop.objects.get_or_create(
                email="info@moonlightjewels.com",
                defaults={
                    "name": "Moonlight Jewels",
                    "owner_name": "Moonlight Owner",
                    "phone_number": "9998887771",
                    "subscription_plan": plan,
                },
            )
            if created_b or not shop_b.active_subscription:
                activate_subscription(shop_b, plan, is_trial=False)

            if not CustomUser.objects.filter(username="admin2").exists():
                CustomUser.objects.create_user(
                    username="admin2",
                    email="admin2@moonlight.com",
                    password="adminpassword2",
                    shop=shop_b,
                    role="ADMIN",
                )
                self.stdout.write(self.style.SUCCESS("Admin user 'admin2' created (password: adminpassword2)"))

            if not CustomUser.objects.filter(username="staff2").exists():
                CustomUser.objects.create_user(
                    username="staff2",
                    email="staff2@moonlight.com",
                    password="staffpassword2",
                    shop=shop_b,
                    role="STAFF",
                )
                self.stdout.write(self.style.SUCCESS("Staff user 'staff2' created (password: staffpassword2)"))
        else:
            self.stdout.write("Seeding Demo data...")
            # Demo Shop
            shop_demo, created_demo = Shop.objects.get_or_create(
                email="demo@jewellery.com",
                defaults={
                    "name": "Golden Demo Jewels",
                    "owner_name": "Demo Owner",
                    "phone_number": "9990001112",
                    "subscription_plan": plan,
                },
            )
            if created_demo or not shop_demo.active_subscription:
                activate_subscription(shop_demo, plan, is_trial=False)

            if not CustomUser.objects.filter(username="demo_admin").exists():
                CustomUser.objects.create_user(
                    username="demo_admin", email="admin@demo.com", password="demopassword", shop=shop_demo, role="ADMIN"
                )
                self.stdout.write(self.style.SUCCESS("Demo Admin user 'demo_admin' created (password: demopassword)"))

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully."))
