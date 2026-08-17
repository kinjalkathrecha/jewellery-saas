from django.conf import settings


def site_settings(request):
    """
    Context processor to inject SaaS site branding details dynamically
    into all templates context scope.
    """
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Aureate"),
        "SITE_TAGLINE": getattr(settings, "SITE_TAGLINE", ""),
        "SITE_DESCRIPTION": getattr(settings, "SITE_DESCRIPTION", ""),
    }
