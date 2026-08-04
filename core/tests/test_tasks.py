from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone

from core.tasks import check_subscriptions_task, send_invoice_email_task
from tests.factories.shop import ShopFactory
from tests.factories.subscriptions import SubscriptionFactory, SubscriptionPlanFactory


@pytest.mark.django_db
class TestCeleryTasks:
    def test_send_invoice_email_task_missing_invoice(self):
        with patch("logging.Logger.error") as mock_log:
            send_invoice_email_task(99999)
            # Verify logger log error message
            mock_log.assert_any_call("Invoice 99999 not found. Cannot send email.")

    def test_check_subscriptions_task_expiring(self):
        shop = ShopFactory(email="owner@example.com", is_active=True)
        plan = SubscriptionPlanFactory(name="Premium")
        # Subscription expiring in 2 days (warning threshold is 3 days)
        sub = SubscriptionFactory(
            shop=shop,
            plan=plan,
            status="ACTIVE",
            expires_at=timezone.now() + timedelta(days=2),
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
            max_products=1000,
            max_users=3,
            duration_days=30,
        )
        shop.active_subscription = sub
        shop.save()

        mail.outbox = []
        check_subscriptions_task()

        # Check if warning email was dispatched
        assert len(mail.outbox) == 1
        assert "Subscription Expiry Warning" in mail.outbox[0].subject
        assert "owner@example.com" in mail.outbox[0].to
