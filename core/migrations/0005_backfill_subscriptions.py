from datetime import timedelta

from django.db import migrations
from django.utils import timezone


def backfill_active_subscriptions(apps, schema_editor):
    Shop = apps.get_model('core', 'Shop')
    Subscription = apps.get_model('core', 'Subscription')
    Payment = apps.get_model('core', 'Payment')
    
    now = timezone.now()
    
    for shop in Shop.objects.all():
        if shop.subscription_plan:
            plan = shop.subscription_plan
            expires_at = now + timedelta(days=plan.duration_days)
            
            # Choose billing cycle
            billing_cycle = 'MONTHLY'
            if plan.duration_days >= 365:
                billing_cycle = 'YEARLY'
            elif plan.duration_days >= 90:
                billing_cycle = 'QUARTERLY'
                
            features_snapshot = {
                'barcode': True,
                'repair': True,
                'crm': True,
                'analytics': True if plan.price > 0 else False,
                'api': True if plan.price > 1000 else False
            }
            
            # 1. Create active subscription history record
            sub = Subscription.objects.create(
                shop=shop,
                plan=plan,
                status='ACTIVE',
                auto_renew=False,
                current_period_start=now,
                current_period_end=expires_at,
                expires_at=expires_at,
                
                plan_name=plan.name,
                plan_price=plan.price,
                max_products=plan.max_products,
                max_users=plan.max_users,
                max_invoices_per_month=1000,
                duration_days=plan.duration_days,
                billing_cycle=billing_cycle,
                features=features_snapshot
            )
            
            # 2. Log corresponding payment
            Payment.objects.create(
                subscription=sub,
                amount=plan.price,
                currency='INR',
                status='SUCCESS',
                gateway='MANUAL',
                payment_reference=f"PAY-BACKFILL-{shop.id}-{now.strftime('%Y%m%d')}",
                paid_at=now
            )
            
            # 3. Connect Shop active_subscription field
            shop.active_subscription = sub
            shop.save()
        else:
            # If they don't have a plan, assign a Trial pointing to the first plan in database
            SubscriptionPlan = apps.get_model('core', 'SubscriptionPlan')
            plan = SubscriptionPlan.objects.first()
            if plan:
                expires_at = now + timedelta(days=7)
                sub = Subscription.objects.create(
                    shop=shop,
                    plan=plan,
                    status='TRIAL',
                    auto_renew=False,
                    current_period_start=now,
                    current_period_end=expires_at,
                    expires_at=expires_at,
                    
                    plan_name=plan.name,
                    plan_price=0.00,
                    max_products=plan.max_products,
                    max_users=plan.max_users,
                    max_invoices_per_month=50,
                    duration_days=7,
                    billing_cycle='MONTHLY',
                    features={
                        'barcode': True,
                        'repair': True,
                        'crm': True,
                        'analytics': False,
                        'api': False
                    }
                )
                shop.active_subscription = sub
                shop.trial_used = True
                shop.save()

def reverse_backfill(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_subscription_shop_trial_used_subscriptionevent_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_active_subscriptions, reverse_backfill),
    ]
