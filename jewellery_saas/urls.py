from django.contrib import admin
from django.urls import include, path

from core.views import (
    about_page,
    contact_page,
    demo_page,
    features_page,
    health_check,
    landing_page,
    pricing_page,
    resources_page,
    robots_txt,
    sitemap_xml,
    submit_lead_api,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
    path("accounts/", include("accounts.urls")),
    path("inventory/", include("inventory.urls")),
    path("customers/", include("customers.urls")),
    path("billing/", include("billing.urls")),
    path("repairs/", include("repairs.urls")),
    path("api/v1/barcodes/", include("barcodes.urls")),
    # Private Dashboard Application
    path("dashboard/", include("dashboard.urls")),
    # Public Marketing Site
    path("", landing_page, name="landing_page"),
    path("features/", features_page, name="features_page"),
    path("pricing/", pricing_page, name="pricing_page"),
    path("demo/", demo_page, name="demo_page"),
    path("contact/", contact_page, name="contact_page"),
    path("about/", about_page, name="about_page"),
    path("resources/", resources_page, name="resources_page"),
    # Unified Lead API Endpoint
    path("api/leads/create/", submit_lead_api, name="submit_lead_api"),
    # Technical SEO Endpoints
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap_xml"),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
