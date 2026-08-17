from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone


def robots_txt(request):
    """
    Serve robots.txt dynamically with search engine indexing preferences
    and sitemap pointers referencing the current host.
    """
    sitemap_url = request.build_absolute_uri(reverse("sitemap_xml"))
    content = (
        f"User-agent: *\nDisallow: /admin/\nDisallow: /dashboard/\nDisallow: /accounts/\n\nSitemap: {sitemap_url}\n"
    )
    return HttpResponse(content, content_type="text/plain")


def sitemap_xml(request):
    """
    Generate sitemap.xml dynamically tracking all public marketing pages
    for optimization in Google Search and crawlers.
    """
    static_urls = [
        "landing_page",
        "features_page",
        "pricing_page",
        "about_page",
        "resources_page",
        "contact_page",
        "demo_page",
    ]

    now_str = timezone.now().strftime("%Y-%m-%d")

    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for url_name in static_urls:
        try:
            loc = request.build_absolute_uri(reverse(url_name))
            xml_parts.append(
                "  <url>\n"
                f"    <loc>{loc}</loc>\n"
                f"    <lastmod>{now_str}</lastmod>\n"
                "    <changefreq>weekly</changefreq>\n"
                "    <priority>0.8</priority>\n"
                "  </url>"
            )
        except Exception:
            continue

    xml_parts.append("</urlset>")

    xml_content = "\n".join(xml_parts)
    return HttpResponse(xml_content, content_type="application/xml")
