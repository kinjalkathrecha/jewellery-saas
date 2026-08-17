from .leads import submit_lead_api
from .marketing import (
    about_page,
    contact_page,
    demo_page,
    features_page,
    health_check,
    landing_page,
    pricing_page,
    resources_page,
)
from .seo import robots_txt, sitemap_xml

__all__ = [
    "about_page",
    "contact_page",
    "demo_page",
    "features_page",
    "health_check",
    "landing_page",
    "pricing_page",
    "resources_page",
    "robots_txt",
    "sitemap_xml",
    "submit_lead_api",
]
