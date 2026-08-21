from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest, HttpResponse

from audit.models import AuditLog
from core.decorators import redis_rate_limit
from core.models import Shop
from core.validators import validate_image_upload
from inventory.models import JewelleryItem


@pytest.mark.django_db
class TestAuditAndSecurity:
    def test_validate_image_upload_size(self):
        # File too large (6MB)
        large_file = SimpleUploadedFile("test.png", b"x" * (6 * 1024 * 1024), content_type="image/png")
        with pytest.raises(ValidationError) as excinfo:
            validate_image_upload(large_file)
        assert "File too large" in str(excinfo.value)

    def test_validate_image_upload_type(self):
        # Invalid extension
        text_file = SimpleUploadedFile("test.txt", b"some text", content_type="text/plain")
        with pytest.raises(ValidationError) as excinfo:
            validate_image_upload(text_file)
        assert "Only JPEG, PNG, WebP allowed" in str(excinfo.value)

    def test_rate_limit_fail_closed(self):
        # Set up a view with rate limit
        @redis_rate_limit("test_fail_closed", limit=1, period=60)
        def dummy_view(request):
            return HttpResponse("Success")

        request = HttpRequest()
        request.path = "/api/v1/test/"
        request.META = {"HTTP_ACCEPT": "application/json", "REMOTE_ADDR": "127.0.0.1"}

        # Mock cache to throw error on cache.get
        with patch("django.core.cache.cache.get", side_effect=Exception("Redis offline")):
            response = dummy_view(request)
            assert response.status_code == 503
            assert b"Service temporarily unavailable" in response.content

    def test_audit_log_creation_and_tracking(self):
        User = get_user_model()
        shop = Shop.objects.create(name="Audit Shop", email="audit@shop.com", phone_number="1234567")
        user = User.objects.create_user(username="auditor", email="audit@user.com", password="password", shop=shop)

        # Mock thread locals to simulate a logged-in request
        from core.middleware import _thread_locals

        _thread_locals.user = user
        _thread_locals.ip_address = "192.168.1.1"

        try:
            # Create a JewelleryItem
            item = JewelleryItem.objects.create(
                shop=shop,
                item_name="Golden Necklace",
                weight_in_grams=Decimal("10.000"),
                price=Decimal("50000.00"),
                making_charges=Decimal("100.00"),
                profit_margin=Decimal("10.00"),
            )

            # Check that an AuditLog entry was created
            log = AuditLog.objects.filter(model_name="JewelleryItem", object_id=item.id).first()
            assert log is not None
            assert log.action == "CREATE"
            assert log.user == user
            assert log.ip_address == "192.168.1.1"
            assert "Golden Necklace" in log.changes["item_name"][1]

            # Update the JewelleryItem
            item.item_name = "Premium Golden Necklace"
            item.save()

            log = AuditLog.objects.filter(model_name="JewelleryItem", object_id=item.id).order_by("-timestamp").first()
            assert log is not None
            assert log.action == "UPDATE"
            assert log.changes["item_name"] == ["Golden Necklace", "Premium Golden Necklace"]

            # Save ID before delete as Django sets pk to None post-delete
            item_id = item.id
            # Delete the JewelleryItem
            item.delete()

            log = AuditLog.objects.filter(model_name="JewelleryItem", object_id=item_id).order_by("-timestamp").first()
            assert log is not None
            assert log.action == "DELETE"
            assert log.changes["item_name"][0] == "Premium Golden Necklace"
        finally:
            # Cleanup thread locals
            if hasattr(_thread_locals, "user"):
                del _thread_locals.user
            if hasattr(_thread_locals, "ip_address"):
                del _thread_locals.ip_address
