import logging
from urllib.parse import urlparse

from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from core.forms import LeadForm
from core.models import Lead

logger = logging.getLogger(__name__)


@require_POST
@csrf_protect
def submit_lead_api(request):
    """
    Unified POST API endpoint to validate and record public leads
    (General Contact, Demo request, or Newsletter Signup).
    Supports UTMS tracking, spam honeypots, and asynchronous/silent email alerts.
    """
    form = LeadForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"success": False, "message": "Form validation failed.", "errors": form.errors}, status=400)

    lead = form.save(commit=False)

    # 1. Determine Acquisition Traffic Source
    referrer = request.META.get("HTTP_REFERER", "")
    lead.source = request.POST.get("source", "").strip()

    if not lead.source:
        if lead.utm_source:
            lead.source = lead.utm_source
        elif referrer:
            try:
                parsed = urlparse(referrer)
                lead.source = parsed.netloc or referrer
            except Exception:
                lead.source = referrer[:100]
        else:
            lead.source = "Direct"

    # 2. Check and handle duplicate new leads from the same email
    existing_lead = Lead.objects.filter(email=lead.email, lead_type=lead.lead_type, status="NEW").first()

    if existing_lead:
        # Append message notes to the existing active lead record
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        existing_lead.notes += f"\n[Duplicate submission at {timestamp}]: {lead.message}"
        existing_lead.save()
        lead = existing_lead
    else:
        lead.save()

    # 3. Trigger alert email to administrators
    try:
        admin_email = getattr(settings, "ADMIN_EMAIL", "admin@aureate.com")
        subject = f"[{settings.SITE_NAME}] New Lead: {lead.get_lead_type_display()} - {lead.name}"

        context = {
            "lead": lead,
            "site_name": settings.SITE_NAME,
        }

        html_message = render_to_string("emails/new_lead.html", context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        logger.exception("Failed to dispatch lead notification email: %s", e)

    return JsonResponse({"success": True, "message": "Thank you! We will get in touch with you shortly."})
