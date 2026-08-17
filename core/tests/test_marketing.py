import pytest
from django.urls import reverse

from core.models import Lead
from tests.factories.shop import ShopFactory


@pytest.mark.django_db
class TestPublicMarketingPages:
    """
    Test suite for public marketing routes, SEO feeds, and redirections.
    """

    def test_marketing_pages_status_codes(self, client):
        """
        Verify that all public marketing urls load with status 200.
        """
        urls = [
            "landing_page",
            "features_page",
            "pricing_page",
            "about_page",
            "resources_page",
            "contact_page",
            "demo_page",
        ]
        for url_name in urls:
            url = reverse(url_name)
            response = client.get(url)
            assert response.status_code == 200

    def test_technical_seo_endpoints(self, client):
        """
        Verify dynamic sitemap and robots endpoints load correctly.
        """
        robots_url = reverse("robots_txt")
        sitemap_url = reverse("sitemap_xml")

        robots_resp = client.get(robots_url)
        assert robots_resp.status_code == 200
        assert "Sitemap:" in robots_resp.content.decode()

        sitemap_resp = client.get(sitemap_url)
        assert sitemap_resp.status_code == 200
        assert "/features/" in sitemap_resp.content.decode()

    def test_anonymous_landing_page_load(self, client):
        """
        An anonymous visitor should see the landing page, not a redirect.
        """
        url = reverse("landing_page")
        response = client.get(url)
        assert response.status_code == 200
        assert "Hero" in response.content.decode() or "Aureate" in response.content.decode()

    def test_authenticated_landing_page_redirect(self, client):
        """
        An authenticated user should be auto-redirected to the dashboard.
        """
        from accounts.models import CustomUser

        shop = ShopFactory()
        user = CustomUser.objects.create_user(
            username="testuser",
            email="testuser@test.com",
            password="password123",
            shop=shop,
        )
        client.force_login(user)

        url = reverse("landing_page")
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse("dashboard:home")

    def test_anonymous_dashboard_redirects_to_login(self, client):
        """
        An anonymous user trying to access the private dashboard should be redirected.
        """
        url = reverse("dashboard:home")
        response = client.get(url)
        assert response.status_code == 302
        assert "login" in response.url


@pytest.mark.django_db
class TestLeadAcquisitionAPI:
    """
    Test suite for lead capture pipelines and AJAX validation API.
    """

    def test_successful_lead_creation(self, client):
        """
        Submitting valid data should save a new Lead to the database.
        """
        url = reverse("submit_lead_api")
        payload = {
            "name": "Kinjal",
            "email": "kinjal@test.com",
            "phone": "9876543210",
            "shop_name": "Shiv Jewellers",
            "message": "Interested in Professional plan",
            "lead_type": "DEMO",
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "search_ads",
            "website": "",  # Honeypot must be empty
        }

        response = client.post(url, payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert Lead.objects.filter(email="kinjal@test.com").exists()

        lead = Lead.objects.get(email="kinjal@test.com")
        assert lead.source == "google"
        assert lead.status == "NEW"

    def test_honeypot_spam_rejection(self, client):
        """
        If the honeypot website field is filled, the request should fail.
        """
        url = reverse("submit_lead_api")
        payload = {
            "name": "Spam Bot",
            "email": "bot@spam.com",
            "lead_type": "CONTACT",
            "website": "http://spambot.com",  # Honeypot field filled
        }

        response = client.post(url, payload)
        assert response.status_code == 400

        data = response.json()
        assert data["success"] is False
        assert "website" in data["errors"]
        assert not Lead.objects.filter(email="bot@spam.com").exists()

    def test_duplicate_lead_merging(self, client):
        """
        Submitting a new inquiry from an email that already has a NEW lead
        should merge notes instead of creating a duplicate record.
        """
        Lead.objects.create(
            name="Rahul",
            email="rahul@test.com",
            lead_type="CONTACT",
            status="NEW",
            message="Original message",
        )

        url = reverse("submit_lead_api")
        payload = {
            "name": "Rahul",
            "email": "rahul@test.com",
            "message": "Secondary message",
            "lead_type": "CONTACT",
            "website": "",
        }

        response = client.post(url, payload)
        assert response.status_code == 200

        # Check that we still have only 1 lead in the database
        assert Lead.objects.filter(email="rahul@test.com").count() == 1

        lead = Lead.objects.get(email="rahul@test.com")
        assert "Original message" in lead.message
        assert "Secondary message" in lead.notes
